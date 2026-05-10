from __future__ import annotations

import os
import re
from typing import Optional, Any

import structlog
from openai import OpenAI

from answer.schemas import PreGradedAnswerResponse, ErrorType

logger = structlog.get_logger(__name__)


class PregradeExplainerService:
    CLI_HINT_RE = re.compile(
        r"(config|show\s+|standby|track|decrement|active|pri\b|grp\b|interface|e\d+/\d+|r\d\b|#)",
        re.IGNORECASE,
    )
    SHOW_CMD_RE = re.compile(r"(show\s+[a-z0-9\s/-]+)", re.IGNORECASE)
    WORD_RE = re.compile(r"[A-Za-zА-Яа-я]+")
    NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")

    def __init__(self) -> None:
        self.client = OpenAI(
            base_url=os.getenv("PRE_GRADE_LLM_BASE_URL", "http://localhost:8080/v1"),
            api_key=os.getenv("PRE_GRADE_LLM_API_KEY", "dummy"),
        )
        self.model = os.getenv("PRE_GRADE_LLM_MODEL", "local-model")

        self.GREETINGS_RE = re.compile(
            r"^(конечно|вот|пожалуйста|хорошо|итог|комментарий|assistant).*?:?\s*",
            re.IGNORECASE,
        )

    def generate(
            self,
            answer: PreGradedAnswerResponse,
            question_text: Optional[str] = None,
    ) -> Optional[str]:
        pre_grade = answer.pre_grade or {}
        if not self._should_generate(pre_grade):
            return None

        student_answer = self._extract_answer_text(answer)
        reference = (answer.reference or "").strip()

        findings = self._build_findings(
            question_text=question_text,
            student_answer=student_answer,
            reference=reference,
            pre_grade=pre_grade,
        )

        deterministic = self._deterministic_explanation(findings)
        if deterministic:
            return deterministic

        user_prompt = self._build_user_prompt(
            question=question_text,
            student_answer=student_answer,
            reference=reference,
            score=float(pre_grade.get("score", 0.0) or 0.0),
            findings=findings,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты пишешь очень короткий комментарий для преподавателя по одному ответу студента. "
                            "Не используй слова 'автопроверка', 'модель', 'LLM'. "
                            "Не обращайся ни к студенту, ни к преподавателю. "
                            "Не предлагай оценку. "
                            "Максимум одно короткое предложение. "
                            "Комментарий должен просто назвать основную проблему ответа человеческим языком."
                        ),
                    },
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=60,
                temperature=0.1,
            )
            raw_text = response.choices[0].message.content
        except Exception as e:
            logger.exception(
                "pregrade.explainer.llm_failed",
                error=str(e),
                answer_id=str(answer.id),
                element_id=str(answer.element_id),
            )
            return self._fallback(findings)

        cleaned = self._post_process(raw_text)
        if not cleaned:
            logger.info(
                "pregrade.explainer.empty_after_postprocess",
                answer_id=str(answer.id),
                element_id=str(answer.element_id),
            )
            return self._fallback(findings)

        logger.info(
            "pregrade.explainer.ok",
            answer_id=str(answer.id),
            element_id=str(answer.element_id),
            text_length=len(cleaned),
        )
        return cleaned

    def _build_user_prompt(
            self,
            *,
            question: Optional[str],
            student_answer: str,
            reference: str,
            score: float,
            findings: dict[str, Any],
    ) -> str:
        question_part = f"Задание: {question.strip()}\n" if question else ""
        reference_part = f"Ожидаемый ответ: {reference}\n" if reference else ""

        return (
            f"{question_part}"
            f"{reference_part}"
            f"Ответ студента: {student_answer or '(пустой ответ)'}\n"
            f"Score: {score}\n"
            f"Диагностика: {findings}\n\n"
            "Сформулируй один короткий комментарий."
        )

    def _build_findings(
            self,
            *,
            question_text: Optional[str],
            student_answer: str,
            reference: str,
            pre_grade: dict[str, Any],
    ) -> dict[str, Any]:
        errors = pre_grade.get("errors", []) or []
        score = float(pre_grade.get("score", 0.0) or 0.0)

        error_summary = self._summarize_errors(errors)
        expected_type = self._classify_expected_type(question_text, reference)
        expected_label = self._build_expected_label(question_text, expected_type)
        actual_type = self._classify_actual_type(student_answer)

        main_problem = self._detect_main_problem(
            expected_type=expected_type,
            actual_type=actual_type,
            error_summary=error_summary,
            score=score,
        )

        return {
            "expected_type": expected_type,
            "expected_label": expected_label,
            "actual_type": actual_type,
            "main_problem": main_problem,
            "score": score,
            "missing_numbers": error_summary["missing_numbers"],
            "missing_literals": error_summary["missing_literals"],
            "missing_keywords": error_summary["missing_keywords"],
            "param_mismatches": error_summary["param_mismatches"],
            "has_regex_no_match": error_summary["has_regex_no_match"],
            "has_semantic_mismatch": error_summary["has_semantic_mismatch"],
            "has_weak_semantic_match": error_summary["has_weak_semantic_match"],
            "has_param_pregrade_failed": error_summary["has_param_pregrade_failed"],
        }

    def _deterministic_explanation(self, findings: dict[str, Any]) -> Optional[str]:
        expected_type = findings["expected_type"]
        expected_label = findings["expected_label"]
        actual_type = findings["actual_type"]
        main_problem = findings["main_problem"]

        missing_numbers = findings["missing_numbers"]
        missing_literals = findings["missing_literals"]
        missing_keywords = findings["missing_keywords"]
        param_mismatches = findings["param_mismatches"]

        if expected_type in {"cli_command", "show_output"}:
            if actual_type == "garbage_text":
                return f"Вместо {expected_label} введён посторонний текст."

            if actual_type == "numeric_only":
                return f"Указано только число, а ожидалась {expected_label}."

            if actual_type == "partial_command":
                return f"{expected_label.capitalize()} указана не полностью."

            if main_problem == "command_format_mismatch":
                return f"{expected_label.capitalize()} не совпадает с ожидаемым форматом."

            if missing_keywords or missing_literals:
                return f"В {expected_label} не хватает обязательных частей."

            if missing_numbers:
                return f"В {expected_label} не хватает обязательных значений."

        if expected_type == "numeric":
            if actual_type == "numeric_only":
                return "Указано число, но оно не совпадает с ожидаемым значением."
            if actual_type in {"garbage_text", "free_text", "command_like", "partial_command"}:
                return "Ожидалось числовое значение, но ответ дан в другом формате."

        if missing_keywords:
            return "Не хватает ключевых терминов."

        if missing_literals:
            return "В ответе отсутствуют обязательные части."

        if missing_numbers:
            return "Не хватает обязательных значений."

        if param_mismatches:
            return "Часть параметров указана неверно."

        return None

    def _fallback(self, findings: dict[str, Any]) -> str:
        deterministic = self._deterministic_explanation(findings)
        if deterministic:
            return deterministic

        main_problem = findings["main_problem"]

        if main_problem == "semantic_mismatch":
            return "Ответ по смыслу не совпадает с ожидаемым."

        if main_problem == "weak_semantic_match":
            return "Ответ близок по смыслу, но сформулирован недостаточно точно."

        return "Ответ не совпадает с ожидаемым содержанием."

    def _post_process(self, text: str) -> str:
        if not text:
            return ""

        text = re.sub(r"<\|.*?\|>", "", text, flags=re.DOTALL).strip()
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()

        lines = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            line = self.GREETINGS_RE.sub("", line).strip()
            if line:
                lines.append(line)

        if not lines:
            return ""

        result = " ".join(lines).strip()
        result = re.sub(r"\s+", " ", result)

        if "." in result:
            result = result.split(".", 1)[0].strip() + "."

        if len(result) > 180:
            result = result[:177].rstrip() + "..."

        return result

    def _summarize_errors(self, errors: list[dict[str, Any]]) -> dict[str, Any]:
        missing_numbers: list[str] = []
        missing_literals: list[str] = []
        missing_keywords: list[str] = []
        param_mismatches: list[str] = []

        has_regex_no_match = False
        has_semantic_mismatch = False
        has_weak_semantic = False
        has_param_pregrade_failed = False

        for err in errors:
            err_type_raw = err.get("type") or ErrorType.SEMANTIC_MISMATCH.value
            expected = str(err.get("expected") or "").strip()

            try:
                err_type = ErrorType(err_type_raw)
            except Exception:
                err_type = ErrorType.SEMANTIC_MISMATCH

            if err_type == ErrorType.MISSING_NUMBER and expected:
                if expected not in missing_numbers:
                    missing_numbers.append(expected)

            elif err_type == ErrorType.LITERAL_MISSING and expected:
                if expected not in missing_literals:
                    missing_literals.append(expected)

            elif err_type == ErrorType.KEYWORD_MISMATCH and expected:
                if expected not in missing_keywords:
                    missing_keywords.append(expected)

            elif err_type == ErrorType.PARAM_MISMATCH and expected:
                if expected not in param_mismatches:
                    param_mismatches.append(expected)

            elif err_type == ErrorType.REGEX_NO_MATCH:
                has_regex_no_match = True

            elif err_type == ErrorType.SEMANTIC_MISMATCH:
                has_semantic_mismatch = True

            elif err_type == ErrorType.WEAK_SEMANTIC_MATCH:
                has_weak_semantic = True

            elif err_type == ErrorType.PARAM_PREGRADE_FAILED:
                has_param_pregrade_failed = True

        return {
            "has_regex_no_match": has_regex_no_match,
            "has_semantic_mismatch": has_semantic_mismatch,
            "has_weak_semantic_match": has_weak_semantic,
            "has_param_pregrade_failed": has_param_pregrade_failed,
            "missing_numbers": missing_numbers,
            "missing_literals": missing_literals,
            "missing_keywords": missing_keywords,
            "param_mismatches": param_mismatches,
        }

    def _classify_expected_type(
            self,
            question_text: Optional[str],
            reference: str,
    ) -> str:
        text = " ".join(
            x for x in [(question_text or "").strip(), reference.strip()] if x
        ).strip()

        if not text:
            return "free_text"

        if self._extract_show_command(text):
            return "show_output"

        if self._looks_like_cli(text):
            return "cli_command"

        if self._looks_like_numeric_reference(reference):
            return "numeric"

        return "free_text"

    def _build_expected_label(
            self,
            question_text: Optional[str],
            expected_type: str,
    ) -> str:
        q = (question_text or "").strip()

        if expected_type == "show_output":
            show_cmd = self._extract_show_command(q)
            if show_cmd:
                return f"строка вывода «{show_cmd}»"
            return "строка вывода"

        if expected_type == "cli_command":
            return "команда"

        if expected_type == "numeric":
            return "числовое значение"

        return "ответ"

    def _classify_actual_type(self, student_answer: str) -> str:
        text = (student_answer or "").strip()
        if not text:
            return "empty"

        if self._looks_like_numeric_only(text):
            return "numeric_only"

        if self._looks_like_cli(text):
            tokens = text.split()
            if len(tokens) <= 3:
                return "partial_command"
            return "command_like"

        words = self.WORD_RE.findall(text)
        numbers = self.NUMBER_RE.findall(text)

        if len(words) <= 1 and len(numbers) <= 1 and len(text) <= 8:
            return "garbage_text"

        return "free_text"

    def _detect_main_problem(
            self,
            *,
            expected_type: str,
            actual_type: str,
            error_summary: dict[str, Any],
            score: float,
    ) -> str:
        if expected_type in {"cli_command", "show_output"}:
            if actual_type == "numeric_only":
                return "single_value_instead_of_command"
            if actual_type == "garbage_text":
                return "garbage_instead_of_command"
            if actual_type == "partial_command":
                return "partial_command"
            if error_summary["has_regex_no_match"]:
                return "command_format_mismatch"

        if expected_type == "numeric":
            if actual_type != "numeric_only":
                return "non_numeric_instead_of_number"
            return "wrong_numeric_value"

        if error_summary["has_weak_semantic_match"]:
            return "weak_semantic_match"

        if error_summary["has_semantic_mismatch"]:
            return "semantic_mismatch"

        if score <= 0.0:
            return "full_mismatch"

        return "partial_mismatch"

    def _extract_show_command(self, text: str) -> Optional[str]:
        if not text:
            return None

        match = self.SHOW_CMD_RE.search(text)
        if not match:
            return None

        value = match.group(1).strip()
        value = re.sub(r"\s+", " ", value)
        return value

    def _looks_like_cli(self, text: str) -> bool:
        return bool(self.CLI_HINT_RE.search(text))

    def _looks_like_numeric_only(self, text: str) -> bool:
        return bool(re.fullmatch(r"\s*-?\d+(?:[.,]\d+)?\s*", text))

    def _looks_like_numeric_reference(self, text: str) -> bool:
        stripped = (text or "").strip()
        if not stripped:
            return False

        if self._looks_like_cli(stripped):
            return False

        return bool(
            re.fullmatch(
                r"-?\d+(?:[.,]\d+)?(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?",
                stripped,
            )
        )

    @staticmethod
    def _extract_answer_text(answer: PreGradedAnswerResponse) -> str:
        data = answer.data or {}
        if not isinstance(data, dict):
            return ""

        nested = data.get("data")
        if isinstance(nested, dict):
            text = nested.get("text")
            if isinstance(text, str):
                return text.strip()

        text = data.get("text")
        if isinstance(text, str):
            return text.strip()

        return ""

    @staticmethod
    def _should_generate(pre_grade: dict[str, Any]) -> bool:
        score = float(pre_grade.get("score", 0.0) or 0.0)
        errors = pre_grade.get("errors", []) or []
        return bool(errors) or score < 1.0