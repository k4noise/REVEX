from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional, Any, List, Tuple

import structlog
from openai import OpenAI

from answer.schemas import PreGradedAnswerResponse
from answer.schemas import ErrorType

logger = structlog.get_logger(__name__)


@dataclass
class AnswerFindings:
    expected_type: str
    actual_type: str
    main_problem: str
    score: float
    missing_numbers: Optional[str]
    missing_literals: Optional[str]
    missing_keywords: Optional[str]
    param_mismatches: List[Tuple[str, Optional[str]]]
    semantic_mismatches: List[Tuple[str, Optional[str]]]
    weak_matches: List[Tuple[str, Optional[str]]]
    has_regex_no_match: bool
    regex_pattern: Optional[str]
    failed_params: Optional[str]


class PregradeExplainerService:
    PATTERN_WORD = re.compile(r'[A-Za-zА-Яа-я]+')
    PATTERN_NUMBER = re.compile(r'-?\d+(?:[.,]\d+)?')
    PATTERN_NUMERIC_ONLY = re.compile(r'\s*-?\d+(?:[.,]\d+)?\s*')
    PATTERN_NUMERIC_REFERENCE = re.compile(r'-?\d+(?:[.,]\d+)?(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?')
    PATTERN_GREETINGS = re.compile(
        r'^(конечно|вот|пожалуйста|хорошо|итог|комментарий|assistant).*?:?\s*',
        re.IGNORECASE,
    )
    PATTERN_SPECIAL_TOKENS = re.compile(r'<\|.*?\|>', re.DOTALL)
    PATTERN_THINK_TAGS = re.compile(r'<think>.*?</think>', re.DOTALL | re.IGNORECASE)
    PATTERN_MULTIPLE_SPACES = re.compile(r'\s+')

    def __init__(self) -> None:
        self.client = OpenAI(
            base_url=os.getenv('PRE_GRADE_LLM_BASE_URL', 'http://localhost:8080/v1'),
            api_key=os.getenv('PRE_GRADE_LLM_API_KEY', 'dummy'),
        )
        self.model = os.getenv('PRE_GRADE_LLM_MODEL', 'local-model')

    def generate(
            self,
            answer: PreGradedAnswerResponse,
            question_text: Optional[str] = None,
    ) -> Optional[str]:
        pre_grade = answer.pre_grade or {}
        if not self._should_generate(pre_grade):
            return None

        student_answer = self._extract_answer_text(answer)
        reference = (answer.reference or '').strip()

        findings = self._analyze_answer(
            question_text=question_text,
            student_answer=student_answer,
            reference=reference,
            pre_grade=pre_grade,
        )

        parts = []

        warning = self._format_warning(findings)
        if warning:
            parts.append(warning)

        summary = self._generate_summary(findings, question_text, student_answer, reference, answer)
        parts.append(summary)

        return '\n'.join(parts)

    def _format_warning(self, findings: AnswerFindings) -> Optional[str]:
        warnings = []

        for expected, actual in findings.param_mismatches:
            if actual:
                warnings.append(f'⚠️ Значение [{actual}] вне диапазона [{expected}]')
            else:
                warnings.append(f'⚠️ Значение вне диапазона [{expected}]')

        if findings.failed_params:
            warnings.append(
                f'⚠️ Зависимость {{{findings.failed_params}}} не проверена — результат может быть неточным'
            )

        if not warnings:
            return None

        return '\n'.join(warnings)

    def _generate_summary(
            self,
            findings: AnswerFindings,
            question_text: Optional[str],
            student_answer: str,
            reference: str,
            answer: PreGradedAnswerResponse,
    ) -> str:
        deterministic = self._generate_deterministic(findings)
        if deterministic:
            return deterministic

        return self._generate_with_llm(
            question=question_text,
            student_answer=student_answer,
            reference=reference,
            score=findings.score,
            findings=findings,
            answer_id=str(answer.id),
            element_id=str(answer.element_id),
        )

    def _generate_deterministic(self, findings: AnswerFindings) -> Optional[str]:
        actual_type = findings.actual_type
        main_problem = findings.main_problem

        if actual_type == 'empty':
            return 'Ответ не заполнен.'

        if actual_type == 'garbage_text':
            return 'Введён посторонний текст.'

        if findings.expected_type == 'numeric':
            if actual_type == 'numeric_only':
                return 'Указано число, но оно не совпадает с ожидаемым значением.'
            return 'Ожидалось числовое значение, но ответ дан в другом формате.'

        if findings.param_mismatches:
            return 'Значение параметра вне допустимого диапазона.'

        if findings.has_regex_no_match:
            return 'Ответ не совпадает с ожидаемым форматом.'

        if findings.missing_keywords:
            return 'Не хватает ключевых терминов.'

        if findings.missing_literals:
            return 'В ответе отсутствуют обязательные части.'

        if findings.missing_numbers:
            return f'Не найдены значения: {findings.missing_numbers}'

        if main_problem == 'semantic_mismatch':
            return 'Ответ по смыслу не совпадает с ожидаемым.'

        if main_problem == 'weak_semantic_match':
            return 'Ответ близок по смыслу, но сформулирован недостаточно точно.'

        return None

    def _generate_with_llm(
            self,
            question: Optional[str],
            student_answer: str,
            reference: str,
            score: float,
            findings: AnswerFindings,
            answer_id: str,
            element_id: str,
    ) -> str:
        prompt = self._build_prompt(
            question=question,
            student_answer=student_answer,
            reference=reference,
            score=score,
            findings=findings,
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            'Ты пишешь очень короткий комментарий для преподавателя по одному ответу студента. '
                            'Не используй слова "автопроверка", "модель", "LLM". '
                            'Не обращайся ни к студенту, ни к преподавателю. '
                            'Не предлагай оценку. '
                            'Максимум одно короткое предложение. '
                            'Комментарий должен просто назвать основную проблему ответа человеческим языком.'
                        ),
                    },
                    {'role': 'user', 'content': prompt},
                ],
                max_tokens=60,
                temperature=0.1,
            )
            raw_response = response.choices[0].message.content
        except Exception as error:
            logger.exception(
                'pregrade.explainer.llm_failed',
                error=str(error),
                answer_id=answer_id,
                element_id=element_id,
            )
            return self._generate_fallback(findings)

        cleaned = self._clean_llm_response(raw_response)
        if not cleaned:
            logger.info(
                'pregrade.explainer.empty_after_cleanup',
                answer_id=answer_id,
                element_id=element_id,
            )
            return self._generate_fallback(findings)

        logger.info(
            'pregrade.explainer.success',
            answer_id=answer_id,
            element_id=element_id,
            response_length=len(cleaned),
        )
        return cleaned

    def _build_prompt(
            self,
            question: Optional[str],
            student_answer: str,
            reference: str,
            score: float,
            findings: AnswerFindings,
    ) -> str:
        parts = []

        if question:
            parts.append(f'Задание: {question.strip()}')

        if reference:
            parts.append(f'Ожидаемый ответ: {reference}')

        parts.append(f'Ответ студента: {student_answer or "(пустой ответ)"}')
        parts.append(f'Score: {score}')
        parts.append(f'Проблема: {findings.main_problem}')
        parts.append('')
        parts.append('Сформулируй один короткий комментарий.')

        return '\n'.join(parts)

    def _generate_fallback(self, findings: AnswerFindings) -> str:
        deterministic = self._generate_deterministic(findings)
        if deterministic:
            return deterministic

        return 'Ответ не совпадает с ожидаемым содержанием.'

    def _clean_llm_response(self, text: str) -> str:
        if not text:
            return ''

        text = self.PATTERN_SPECIAL_TOKENS.sub('', text).strip()
        text = self.PATTERN_THINK_TAGS.sub('', text).strip()

        lines = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            line = self.PATTERN_GREETINGS.sub('', line).strip()
            if line:
                lines.append(line)

        if not lines:
            return ''

        result = ' '.join(lines).strip()
        result = self.PATTERN_MULTIPLE_SPACES.sub(' ', result)

        if '.' in result:
            result = result.split('.', 1)[0].strip() + '.'

        if len(result) > 180:
            result = result[:177].rstrip() + '...'

        return result

    def _analyze_answer(
            self,
            question_text: Optional[str],
            student_answer: str,
            reference: str,
            pre_grade: dict[str, Any],
    ) -> AnswerFindings:
        errors = pre_grade.get('errors', []) or []
        score = float(pre_grade.get('score', 0.0) or 0.0)

        error_summary = self._summarize_errors(errors)
        expected_type = self._classify_expected_type(reference)
        actual_type = self._classify_actual_type(student_answer)

        main_problem = self._detect_main_problem(
            expected_type=expected_type,
            actual_type=actual_type,
            error_summary=error_summary,
            score=score,
        )

        return AnswerFindings(
            expected_type=expected_type,
            actual_type=actual_type,
            main_problem=main_problem,
            score=score,
            missing_numbers=error_summary['missing_numbers'],
            missing_literals=error_summary['missing_literals'],
            missing_keywords=error_summary['missing_keywords'],
            param_mismatches=error_summary['param_mismatches'],
            semantic_mismatches=error_summary['semantic_mismatches'],
            weak_matches=error_summary['weak_matches'],
            has_regex_no_match=error_summary['has_regex_no_match'],
            regex_pattern=error_summary['regex_pattern'],
            failed_params=error_summary['failed_params'],
        )

    def _summarize_errors(self, errors: list[dict[str, Any]]) -> dict[str, Any]:
        param_mismatches: List[Tuple[str, Optional[str]]] = []
        semantic_mismatches: List[Tuple[str, Optional[str]]] = []
        weak_matches: List[Tuple[str, Optional[str]]] = []

        has_regex_no_match = False
        regex_pattern: Optional[str] = None
        failed_params: Optional[str] = None
        missing_numbers: Optional[str] = None
        missing_literals: Optional[str] = None
        missing_keywords: Optional[str] = None

        for error in errors:
            error_type_raw = error.get('type') or ErrorType.SEMANTIC_MISMATCH.value
            expected = str(error.get('expected') or '').strip()
            actual = error.get('actual')
            actual_str = str(actual).strip() if actual else None

            try:
                error_type = ErrorType(error_type_raw)
            except Exception:
                error_type = ErrorType.SEMANTIC_MISMATCH

            if error_type == ErrorType.MISSING_NUMBER and expected:
                missing_numbers = expected

            elif error_type == ErrorType.LITERAL_MISSING and expected:
                missing_literals = expected

            elif error_type == ErrorType.KEYWORD_MISMATCH and expected:
                missing_keywords = expected

            elif error_type == ErrorType.PARAM_MISMATCH:
                param_mismatches.append((expected, actual_str))

            elif error_type == ErrorType.REGEX_NO_MATCH:
                has_regex_no_match = True
                if expected:
                    regex_pattern = expected

            elif error_type == ErrorType.SEMANTIC_MISMATCH:
                semantic_mismatches.append((expected, actual_str))

            elif error_type == ErrorType.WEAK_SEMANTIC_MATCH:
                weak_matches.append((expected, actual_str))

            elif error_type == ErrorType.PARAM_PREGRADE_FAILED:
                failed_params = expected

        return {
            'missing_numbers': missing_numbers,
            'missing_literals': missing_literals,
            'missing_keywords': missing_keywords,
            'param_mismatches': param_mismatches,
            'semantic_mismatches': semantic_mismatches,
            'weak_matches': weak_matches,
            'has_regex_no_match': has_regex_no_match,
            'regex_pattern': regex_pattern,
            'failed_params': failed_params,
        }

    def _classify_expected_type(self, reference: str) -> str:
        stripped = (reference or '').strip()
        if not stripped:
            return 'free_text'

        if self.PATTERN_NUMERIC_REFERENCE.fullmatch(stripped):
            return 'numeric'

        return 'free_text'

    def _classify_actual_type(self, student_answer: str) -> str:
        text = (student_answer or '').strip()
        if not text:
            return 'empty'

        if self.PATTERN_NUMERIC_ONLY.fullmatch(text):
            return 'numeric_only'

        words = self.PATTERN_WORD.findall(text)
        numbers = self.PATTERN_NUMBER.findall(text)

        if len(words) <= 1 and len(numbers) <= 1 and len(text) <= 8:
            return 'garbage_text'

        return 'free_text'

    def _detect_main_problem(
            self,
            expected_type: str,
            actual_type: str,
            error_summary: dict[str, Any],
            score: float,
    ) -> str:
        if actual_type == 'empty':
            return 'empty_answer'

        if actual_type == 'garbage_text':
            return 'garbage_input'

        if expected_type == 'numeric' and actual_type != 'numeric_only':
            return 'type_mismatch'

        if error_summary['param_mismatches']:
            return 'param_out_of_range'

        if error_summary['has_regex_no_match']:
            return 'format_mismatch'

        if error_summary['weak_matches']:
            return 'weak_semantic_match'

        if error_summary['semantic_mismatches']:
            return 'semantic_mismatch'

        if score <= 0.0:
            return 'full_mismatch'

        return 'partial_mismatch'

    @staticmethod
    def _extract_answer_text(answer: PreGradedAnswerResponse) -> str:
        data = answer.data or {}
        if not isinstance(data, dict):
            return ''

        nested = data.get('data')
        if isinstance(nested, dict):
            text = nested.get('text')
            if isinstance(text, str):
                return text.strip()

        text = data.get('text')
        if isinstance(text, str):
            return text.strip()

        return ''

    @staticmethod
    def _should_generate(pre_grade: dict[str, Any]) -> bool:
        score = float(pre_grade.get('score', 0.0) or 0.0)
        errors = pre_grade.get('errors', []) or []
        return bool(errors) or score < 1.0