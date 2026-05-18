from __future__ import annotations

import re
from dataclasses import asdict
from typing import Sequence, Optional, Dict, List

from answer.schemas import AnswerResponse, PreGradedAnswerResponse
from answer.schemas import GradingContext, GradeResult, ErrorDetail, ErrorType

from answer.graders.config import GraderConfig, DEFAULT_CONFIG
from answer.graders.pipeline import GraderPipeline
from answer.graders.parametrized import ParametrizedGrader
from answer.graders.numbers import NumbersGrader
from answer.graders.fuzzy import FuzzyGrader
from answer.graders.strict import StrictMatchGrader
from answer.graders.thesis import ThesisGrader
from answer.utils.embedder import TextEmbedder


class PreGraderService:
    PATTERN_WHITESPACE = re.compile(r'\s+')

    def __init__(
            self,
            answers: Sequence[AnswerResponse],
            embedder: Optional[TextEmbedder] = None,
            parameters: Optional[Dict[str, AnswerResponse]] = None,
            config: GraderConfig = DEFAULT_CONFIG,
    ) -> None:
        self._answers = list(answers or [])
        self._config = config

        self._parameters = parameters or {
            str(answer.element_id): answer
            for answer in self._answers
            if answer.element_id
        }

        self._embedder = embedder or TextEmbedder()

        self._param_grader = ParametrizedGrader(self._parameters, config=config)
        self._numbers_grader = NumbersGrader(config=config)
        self._fuzzy_grader = FuzzyGrader(config=config)
        self._strict_grader = StrictMatchGrader(config=config)
        self._thesis_grader = ThesisGrader(self._embedder, config=config)

    def grade(self, answer: AnswerResponse) -> Optional[PreGradedAnswerResponse]:
        return self._run(answer, fast_mode=True)

    def grade_full(self, answer: AnswerResponse) -> Optional[PreGradedAnswerResponse]:
        return self._run(answer, fast_mode=False)

    def grade_all(self) -> list[PreGradedAnswerResponse]:
        return [
            result for answer in self._answers
            if (result := self.grade_full(answer)) is not None
        ]

    def _run(
            self,
            answer: AnswerResponse,
            fast_mode: bool
    ) -> Optional[PreGradedAnswerResponse]:
        context = self._init_context(answer, fast_mode)
        if context is None:
            return None

        graders = [
            self._param_grader,
            self._numbers_grader,
        ]

        if context.strict_match:
            graders.append(self._strict_grader)
        else:
            graders.extend([
                self._fuzzy_grader,
                self._thesis_grader,
            ])

        pipeline = GraderPipeline(graders, self._config)
        pipeline.run(context)

        return self._build_response(answer, context)

    def _init_context(
            self,
            answer: AnswerResponse,
            fast_mode: bool
    ) -> Optional[GradingContext]:
        if not answer.data or not answer.reference:
            return None

        user_text = self._extract_user_text(answer)
        if not user_text:
            return None

        strict_match = self._extract_strict_match_flag(answer)

        normalized_given = self._normalize(user_text)
        normalized_reference = self._normalize(answer.reference)

        return GradingContext(
            raw_given=normalized_given,
            raw_reference=normalized_reference,
            fast_mode=fast_mode,
            strict_match=strict_match,
        )

    def _build_response(
            self,
            answer: AnswerResponse,
            context: GradingContext
    ) -> PreGradedAnswerResponse:
        score = context.final_score

        consolidated_errors = self._consolidate_errors(context.errors)

        has_param_mismatch = any(
            e.type == ErrorType.PARAM_MISMATCH for e in context.errors
        )

        needs_review = has_param_mismatch or (
                self._config.review_threshold_low
                <= score <=
                self._config.review_threshold_high
        )

        result = GradeResult(
            score=score,
            errors=consolidated_errors,
            needs_manual_review=needs_review,
        )

        return PreGradedAnswerResponse.from_response(answer, asdict(result))

    def _consolidate_errors(self, errors: List[ErrorDetail]) -> List[ErrorDetail]:
        if not errors:
            return errors

        has_regex_no_match = any(e.type == ErrorType.REGEX_NO_MATCH for e in errors)
        has_type_mismatch = any(e.type in {
            ErrorType.LITERAL_MISSING,
            ErrorType.KEYWORD_MISMATCH
        } for e in errors)

        result: List[ErrorDetail] = []

        param_failed = [e.expected for e in errors if e.type == ErrorType.PARAM_PREGRADE_FAILED]
        if param_failed:
            result.append(ErrorDetail(
                type=ErrorType.PARAM_PREGRADE_FAILED,
                expected=', '.join(param_failed)
            ))

        for error in errors:
            if error.type == ErrorType.REGEX_NO_MATCH:
                result.append(error)
                break

        for error in errors:
            if error.type == ErrorType.PARAM_MISMATCH:
                result.append(error)

        if has_regex_no_match:
            return result

        missing_numbers = [e.expected for e in errors if e.type == ErrorType.MISSING_NUMBER]
        if missing_numbers:
            result.append(ErrorDetail(
                type=ErrorType.MISSING_NUMBER,
                expected=', '.join(missing_numbers[:5]) + (' и др.' if len(missing_numbers) > 5 else '')
            ))

        missing_literals = [e.expected for e in errors if e.type == ErrorType.LITERAL_MISSING]
        if missing_literals:
            result.append(ErrorDetail(
                type=ErrorType.LITERAL_MISSING,
                expected=', '.join(missing_literals[:3]) + (' и др.' if len(missing_literals) > 3 else '')
            ))

        missing_keywords = [e.expected for e in errors if e.type == ErrorType.KEYWORD_MISMATCH]
        if missing_keywords:
            result.append(ErrorDetail(
                type=ErrorType.KEYWORD_MISMATCH,
                expected=', '.join(missing_keywords[:3]) + (' и др.' if len(missing_keywords) > 3 else '')
            ))

        if has_type_mismatch:
            return result

        semantic_errors = [e for e in errors if e.type == ErrorType.SEMANTIC_MISMATCH]
        for error in semantic_errors[:2]:
            result.append(error)

        weak_errors = [e for e in errors if e.type == ErrorType.WEAK_SEMANTIC_MATCH]
        for error in weak_errors[:2]:
            result.append(error)

        return result

    def _extract_user_text(self, answer: AnswerResponse) -> str:
        if not isinstance(answer.data, dict):
            return ''

        nested_data = answer.data.get('data')
        if isinstance(nested_data, dict):
            text = nested_data.get('text', '')
            if text:
                return text

        return answer.data.get('text', '') or ''

    def _extract_strict_match_flag(self, answer: AnswerResponse) -> bool:
        if not isinstance(answer.data, dict):
            return False

        properties = answer.data.get('properties')
        if isinstance(properties, dict):
            return bool(properties.get('strict_match', False))

        return False

    def _normalize(self, text: str) -> str:
        return self.PATTERN_WHITESPACE.sub(' ', text.lower()).strip()