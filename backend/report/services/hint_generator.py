import os
import re
from typing import Optional, Sequence

import structlog
from openai import AsyncOpenAI

from answer.schemas import ErrorDetail, ErrorType
from report.schemas.hint import HintGenerationRequest

logger = structlog.get_logger(__name__)

GREETINGS_RE = re.compile(
    r"^(Привет!?|Здравствуй!?|Добрый день!?|Подсказка:)\s*",
    re.IGNORECASE,
)


class HintGenerator:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            base_url=os.getenv("LLM_BASE_URL", "http://localhost:8080/v1"),
            api_key=os.getenv("LLM_API_KEY", "dummy"),
        )
        self.model = os.getenv("LLM_MODEL", "local-model")

    def _post_process(self, text: str) -> str:
        if not text:
            return ""

        text = re.sub(r"<\|.*?\|>", "", text, flags=re.DOTALL).strip()

        think_match = re.search(r"\s*(.*)", text, flags=re.DOTALL)
        if think_match:
            text = think_match.group(1).strip()
        else:
            text = re.sub(r".*?", "", text, flags=re.DOTALL).strip()

        text = re.sub(r"`[^`]+`", "[команда]", text)

        cleaned_lines = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            line = GREETINGS_RE.sub("", line).strip()
            if line:
                cleaned_lines.append(line)

        if not cleaned_lines:
            return ""

        result = cleaned_lines[0]

        question_match = re.match(r"^(.*?\?)", result)
        if question_match:
            result = question_match.group(1)

        if len(result) > 150:
            sentences = re.split(r"(?<=[.?!])\s+", result)
            result = sentences[0] if sentences else result[:150]

        return result

    def _mask_reference(self, text: str, reference: Optional[str]) -> str:
        if not text or not reference:
            return text
        ref = str(reference).strip()
        if not ref:
            return text

        if ref in text:
            return text.replace(ref, "[скрыто]")

        return text

    def _build_user_prompt(
            self,
            theory: str,
            student_answer: str,
            question: Optional[str],
            error: ErrorDetail,
    ) -> str:
        question_part = f"Вопрос: {question}\n" if question else ""
        theory_part = f"Данные:\n{theory[:2000]}\n" if theory else ""
        error_desc = (
            f"Ошибка: {error.type.value}. Ожидалось: {error.expected}. Фактически: {error.actual}\n"
            if error else ""
        )

        return f"""{question_part}{theory_part}{error_desc}
Студент написал: {student_answer or '(пусто)'}
Это неправильно.

Задай ОДИН короткий наводящий вопрос (до 15 слов).
Если есть таблица — укажи конкретный столбец/строку.
Если таблицы нет — укажи, ЧТО именно не хватает или ЧТО неверно в ответе (шаг, значение, логика).
Не перечисляй значения. Не давай готовый ответ. Не пиши приветствия."""

    def _parse_error_detail(self, raw) -> Optional[ErrorDetail]:
        if raw is None:
            return None
        if isinstance(raw, ErrorDetail):
            return raw
        if isinstance(raw, dict):
            try:
                error_type = raw.get("type", "")
                if isinstance(error_type, str):
                    error_type = ErrorType(error_type)
                return ErrorDetail(
                    type=error_type,
                    expected=raw.get("expected", ""),
                    actual=raw.get("actual", ""),
                )
            except (ValueError, KeyError) as e:
                logger.warning("hint.parse_error_detail.failed", error=str(e), raw=raw)
                return None
        return None

    def _pick_best_error(self, errors: Sequence[ErrorDetail]) -> Optional[ErrorDetail]:
        if not errors:
            return None

        priority = {
            ErrorType.PARAM_MISMATCH: 1,
            ErrorType.MISSING_NUMBER: 2,
            ErrorType.KEYWORD_MISMATCH: 3,
            ErrorType.LITERAL_MISSING: 4,
            ErrorType.REGEX_NO_MATCH: 5,
            ErrorType.SEMANTIC_MISMATCH: 6,
            ErrorType.WEAK_SEMANTIC_MATCH: 7,
        }

        return min(errors, key=lambda e: priority.get(e.type, 99))

    async def generate(self, hint_request: HintGenerationRequest) -> Optional[str]:
        theory_list = hint_request.theory or []
        theory_text = "\n\n".join(t for t in theory_list if t)

        error_detail = self._parse_error_detail(hint_request.error_detail)
        if not error_detail:
            logger.info("hint.generate.no_error_detail")
            return None

        all_errors = [error_detail]
        if hasattr(hint_request, "all_errors") and hint_request.all_errors:
            all_errors = [
                self._parse_error_detail(e) or error_detail
                for e in hint_request.all_errors
            ]

        best_error = self._pick_best_error(all_errors) or error_detail

        user_prompt = self._build_user_prompt(
            theory=theory_text,
            student_answer=hint_request.answer,
            question=hint_request.question,
            error=best_error,
        )

        logger.info(
            "hint.generate.prompt",
            theory_length=len(theory_text),
            theory_preview=theory_text[:500],
            question=hint_request.question[:100] if hint_request.question else None,
            answer=hint_request.answer[:100] if hint_request.answer else None,
            error_type=best_error.type.value,
            expected_preview=str(best_error.expected)[:100],
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты помогаешь студенту найти ошибку в ответе. "
                            "Пиши ОДИН короткий наводящий вопрос (до 15 слов). "
                            "Если есть таблица — укажи столбец/строку. "
                            "Если таблицы нет — укажи конкретно: чего не хватает или что неверно (шаг, значение, логика). "
                            "Не давай готовый ответ. Не перечисляй данные. /no_think"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Вопрос: Найдите X = A - B.\n"
                            "Данные:\nТаблица:\nИмя | Значение\nA | 50\nB | 20\n\n"
                            "Студент написал: 100\nЭто неправильно.\n\n"
                            "Задай ОДИН короткий наводящий вопрос (до 15 слов)."
                        ),
                    },
                    {
                        "role": "assistant",
                        "content": "Какая разница между A и B в таблице?",
                    },
                    {
                        "role": "user",
                        "content": (
                            "Вопрос: Решите уравнение 2x + 5 = 15.\n"
                            "Данные: Правила решения линейных уравнений\n"
                            "Студент написал: x=3\nЭто неправильно.\n\n"
                            "Задай ОДИН короткий наводящий вопрос (до 15 слов)."
                        ),
                    },
                    {
                        "role": "assistant",
                        "content": "Какой шаг решения ты пропустил?",
                    },
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=35,
                temperature=0.1,
            )
            raw_text = response.choices[0].message.content
        except Exception as e:
            logger.exception("hint.generate.llm_failed", error=str(e))
            return None

        cleaned = self._post_process(raw_text)
        if not cleaned:
            logger.info("hint.generate.empty_after_postprocess")
            return None

        masked = self._mask_reference(cleaned, best_error.expected)

        logger.info(
            "hint.generate.ok",
            hint_length=len(masked or ""),
            error_type=best_error.type.value,
            has_theory=bool(theory_text),
        )

        return masked