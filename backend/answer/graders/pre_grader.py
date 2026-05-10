from __future__ import annotations

import re
from dataclasses import asdict
from typing import Sequence, Optional, Dict

from answer.schemas import (
    AnswerResponse,
    PreGradedAnswerResponse,
    GradingContext,
    GradeResult,
    ErrorType,
)
from answer.graders.param import ParametrizedAnswerGrader
from answer.graders.fixed import FixedAnswerGrader
from answer.graders.thesis import ThesisAnswerGrader
from answer.utils.embedder import TextEmbedder


class PreGraderService:
    _RE_SPACE = re.compile(r"\s+")
    REVIEW_THRESHOLD_LOW = 0.7
    REVIEW_THRESHOLD_HIGH = 0.9

    def __init__(
            self,
            answers: Sequence[AnswerResponse],
            embedder: Optional[TextEmbedder] = None,
            parameters: Optional[Dict[str, AnswerResponse]] = None,
    ) -> None:
        self._answers: list[AnswerResponse] = list(answers or [])

        self._parameters: Dict[str, AnswerResponse] = parameters or {
            str(a.element_id): a
            for a in self._answers
            if a.element_id
        }

        self._param_grader = ParametrizedAnswerGrader(self._parameters)
        self._fixed_grader = FixedAnswerGrader()
        self._thesis_grader = ThesisAnswerGrader(embedder or TextEmbedder())

    def grade(self, answer: AnswerResponse) -> Optional[PreGradedAnswerResponse]:
        return self._run_pipeline(answer, fast_mode=True)

    def grade_full(self, answer: AnswerResponse) -> Optional[PreGradedAnswerResponse]:
        return self._run_pipeline(answer, fast_mode=False)

    def grade_all(self) -> list[PreGradedAnswerResponse]:
        results: list[PreGradedAnswerResponse] = []
        for answer in self._answers:
            res = self.grade_full(answer)
            if res is not None:
                results.append(res)
        return results

    def _run_pipeline(
            self,
            answer: AnswerResponse,
            fast_mode: bool,
    ) -> Optional[PreGradedAnswerResponse]:
        element_props = {}
        if answer.data and isinstance(answer.data, dict):
            props = answer.data.get("properties")
            if isinstance(props, dict):
                element_props = dict(props)

        strict_match = element_props.get("strict_match", False)

        ctx = self._init_context(answer, fast_mode, strict_match)
        if not ctx:
            return None

        self._param_grader.process(ctx)
        if ctx.should_stop:
            return self._build_response(answer, ctx)

        self._fixed_grader.process_numbers(ctx)
        if ctx.should_stop:
            return self._build_response(answer, ctx)

        if ctx.strict_match:
            self._fixed_grader.process_strict_log(ctx)
            return self._build_response(answer, ctx)

        self._fixed_grader.process_fuzz(ctx)
        if ctx.is_perfect_match or ctx.should_stop:
            return self._build_response(answer, ctx)

        self._thesis_grader.process(ctx)

        return self._build_response(answer, ctx)

    def _init_context(
            self,
            answer: AnswerResponse,
            fast_mode: bool,
            strict_match: bool,
    ) -> Optional[GradingContext]:
        if not answer.data or not answer.reference:
            return None

        user_text = ""
        if isinstance(answer.data, dict):
            nested = answer.data.get("data")
            if isinstance(nested, dict):
                user_text = nested.get("text", "") or ""
            if not user_text:
                user_text = answer.data.get("text", "") or ""

        if not user_text:
            return None

        def normalize(text: str) -> str:
            return self._RE_SPACE.sub(" ", text.lower()).strip()

        norm_given = normalize(user_text)
        norm_ref = normalize(answer.reference)

        return GradingContext(
            original_given=norm_given,
            original_reference=norm_ref,
            resolved_reference=norm_ref,
            current_given=norm_given,
            current_reference=norm_ref,
            fast_mode=fast_mode,
            strict_match=strict_match,
        )

    def _build_response(
            self,
            answer: AnswerResponse,
            ctx: GradingContext,
    ) -> PreGradedAnswerResponse:
        has_fatal_errors = any(
            e.type != ErrorType.PARAM_PREGRADE_FAILED for e in ctx.errors
        )
        score = ctx.final_score if not has_fatal_errors else 0.0

        needs_review = (
                self.REVIEW_THRESHOLD_LOW <= score <= self.REVIEW_THRESHOLD_HIGH
        )

        result = GradeResult(
            score=score,
            errors=ctx.errors,
            needs_manual_review=needs_review,
        )

        return PreGradedAnswerResponse.from_response(answer, asdict(result))