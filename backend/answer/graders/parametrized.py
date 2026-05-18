from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Tuple

from answer.graders.base import BaseGrader
from answer.schemas import AnswerResponse
from answer.schemas import GradingContext, ErrorDetail, ErrorType
from answer.graders.range_spec import RangeSpec


@dataclass
class LineProcessingResult:
    resolved_line: str
    remaining_given: str
    matched_numbers: set[str] = field(default_factory=set)
    errors: list[ErrorDetail] = field(default_factory=list)


class ParametrizedGrader(BaseGrader):
    PATTERN_PARAM = re.compile(r'\{([^}]+)\}')
    PATTERN_RANGE = re.compile(r'\[(.*?)\]')
    PATTERN_WHITESPACE = re.compile(r'\s+')
    PATTERN_LITERAL_BRACKETS = re.compile(r'\[\[(.+?)\]\]')
    PATTERN_HAS_SUBSTITUTIONS = re.compile(r'\{.*?\}|\[.*?\]')

    def __init__(self, parameters: Dict[str, AnswerResponse], **kwargs):
        super().__init__(**kwargs)
        self._parameters = parameters

    def process(self, context: GradingContext) -> None:
        if not self.PATTERN_HAS_SUBSTITUTIONS.search(context.raw_reference):
            return

        reference_lines = [
            line.strip()
            for line in context.raw_reference.splitlines()
            if line.strip()
        ]

        resolved_lines: list[str] = []
        current_given = context.remaining_given
        all_matched_numbers: set[str] = set()

        for line in reference_lines:
            if not self.PATTERN_HAS_SUBSTITUTIONS.search(line):
                resolved_lines.append(line)
                continue

            result = self._process_line(line, current_given)

            resolved_lines.append(result.resolved_line)
            current_given = result.remaining_given
            all_matched_numbers.update(result.matched_numbers)

            for error in result.errors:
                context.add_error(error)

        joined_resolved = '\n'.join(resolved_lines)
        context.resolved_reference = self.PATTERN_WHITESPACE.sub(' ', joined_resolved).strip()
        context.remaining_given = self.PATTERN_WHITESPACE.sub(' ', current_given).strip()
        context.remaining_reference = context.resolved_reference
        context.numbers_checked_by_params = all_matched_numbers

    def _process_line(self, line: str, given: str) -> LineProcessingResult:
        errors: List[ErrorDetail] = []
        matched_numbers: set[str] = set()

        substituted_line, param_errors = self._substitute_params(line)
        errors.extend(param_errors)

        protected_line, protected_ranges = self._protect_literal_brackets(substituted_line)

        regex_pattern, range_specs = self._build_regex_pattern(protected_line, protected_ranges)

        if not range_specs:
            resolved = self.PATTERN_LITERAL_BRACKETS.sub(r'[\1]', protected_line)
            return LineProcessingResult(
                resolved_line=resolved,
                remaining_given=given,
                errors=errors
            )

        compiled_pattern = self._compile_pattern(regex_pattern)
        match_result = compiled_pattern.search(given)

        if match_result:
            resolved = self._apply_matched_values(protected_line, match_result, range_specs)

            for group_index, (spec, raw_spec) in enumerate(range_specs, start=1):
                matched_value = match_result.group(group_index)
                if spec.is_numeric:
                    matched_numbers.add(matched_value.replace(',', '.'))

                if not spec.match(matched_value):
                    errors.append(ErrorDetail(
                        type=ErrorType.PARAM_MISMATCH,
                        expected=raw_spec,
                        actual=matched_value
                    ))

            updated_given = self._blank_matched_regions(given, match_result, len(range_specs))
        else:
            resolved = self._apply_fallback_values(protected_line, range_specs)
            updated_given = given
            errors.append(ErrorDetail(
                type=ErrorType.REGEX_NO_MATCH,
                expected=protected_line
            ))

        resolved = self.PATTERN_LITERAL_BRACKETS.sub(r'[\1]', resolved)

        return LineProcessingResult(
            resolved_line=resolved,
            remaining_given=updated_given,
            matched_numbers=matched_numbers,
            errors=errors
        )

    def _substitute_params(self, line: str) -> Tuple[str, List[ErrorDetail]]:
        errors: List[ErrorDetail] = []

        def replacer(match: re.Match) -> str:
            param_id = match.group(1)
            param = self._parameters.get(param_id)

            if not param:
                return match.group(0)

            data = param.data or {}
            inner_data = data.get('data') or data
            text_value = inner_data.get('text', '') or ''

            if not text_value:
                return match.group(0)

            pre_grade = getattr(param, 'pre_grade', None) or data.get('pre_grade') or {}
            if pre_grade.get('score', 1) == 0:
                errors.append(ErrorDetail(
                    type=ErrorType.PARAM_PREGRADE_FAILED,
                    expected=param_id
                ))

            return text_value

        return self.PATTERN_PARAM.sub(replacer, line), errors

    def _protect_literal_brackets(self, text: str) -> Tuple[str, List[Tuple[int, int]]]:
        result = ''
        protected_ranges: List[Tuple[int, int]] = []
        last_end = 0

        for match in self.PATTERN_LITERAL_BRACKETS.finditer(text):
            start, end = match.span()
            content = match.group(1)
            result += text[last_end:start] + '[' + content + ']'

            protected_start = len(result) - len(content) - 2
            protected_end = len(result)
            protected_ranges.append((protected_start, protected_end))

            last_end = end

        result += text[last_end:]
        return result, protected_ranges

    def _build_regex_pattern(
            self,
            text: str,
            protected_ranges: List[Tuple[int, int]]
    ) -> Tuple[str, List[Tuple[RangeSpec, str]]]:
        pattern_parts = ''
        range_specs: List[Tuple[RangeSpec, str]] = []
        cursor = 0

        for match in self.PATTERN_RANGE.finditer(text):
            start, end = match.span()

            is_protected = any(
                start >= prot_start and end <= prot_end
                for prot_start, prot_end in protected_ranges
            )
            if is_protected:
                continue

            pattern_parts += re.escape(text[cursor:start])
            raw_spec = match.group(1)
            spec = RangeSpec.from_raw(raw_spec)
            range_specs.append((spec, raw_spec))
            pattern_parts += spec.regex_fragment()
            cursor = end

        pattern_parts += re.escape(text[cursor:])
        return pattern_parts, range_specs

    def _apply_matched_values(
            self,
            text: str,
            match_result: re.Match,
            range_specs: List[Tuple[RangeSpec, str]]
    ) -> str:
        group_index = [1]

        def replacer(match: re.Match) -> str:
            value = match_result.group(group_index[0])
            group_index[0] += 1
            return value

        return self.PATTERN_RANGE.sub(replacer, text)

    def _apply_fallback_values(
            self,
            text: str,
            range_specs: List[Tuple[RangeSpec, str]]
    ) -> str:
        spec_iterator = iter(range_specs)

        def replacer(match: re.Match) -> str:
            spec, _ = next(spec_iterator)
            return spec.get_fallback_value()

        return self.PATTERN_RANGE.sub(replacer, text)

    def _blank_matched_regions(
            self,
            text: str,
            match_result: re.Match,
            num_groups: int
    ) -> str:
        chars = list(text)
        for group_index in range(1, num_groups + 1):
            start, end = match_result.span(group_index)
            for position in range(start, end):
                chars[position] = ' '
        return ''.join(chars)

    @staticmethod
    @lru_cache(maxsize=512)
    def _compile_pattern(pattern: str) -> re.Pattern:
        return re.compile(pattern, re.IGNORECASE)