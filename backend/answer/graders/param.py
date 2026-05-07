import re
from functools import lru_cache
from typing import Dict, List, Tuple

from answer.schemas import AnswerResponse, GradingContext, ErrorDetail, ErrorType
from answer.graders.range_spec import RangeSpec


class ParametrizedAnswerGrader:
    _RE_PARAM = re.compile(r"\{([^}]+)}")
    _RE_RANGE = re.compile(r"\[(.*?)\]")
    _RE_SPACE = re.compile(r"\s+")
    _RE_LITERAL_ESCAPE = re.compile(r"\[\[(.+?)]]")
    _RE_PRESENCE_CHECK = re.compile(r'\{.*?\}|\[.*?\]')

    def __init__(self, parameters: Dict[str, AnswerResponse]):
        self._parameters = parameters

    def process(self, ctx: GradingContext) -> None:
        if not self._RE_PRESENCE_CHECK.search(ctx.current_reference):
            return

        lines = [line.strip() for line in ctx.current_reference.splitlines() if line.strip()]
        new_ref_lines = []
        resolved_ref_lines = []
        current_given = ctx.current_given

        for line in lines:
            if not self._RE_PRESENCE_CHECK.search(line):
                new_ref_lines.append(line)
                resolved_ref_lines.append(line)
                continue

            errors, given_mutated, ref_mutated, resolved_line = self._process_line(line, current_given)
            current_given = given_mutated
            new_ref_lines.append(ref_mutated)
            resolved_ref_lines.append(resolved_line)

            for err in errors:
                ctx.add_error(err)
                if ctx.should_stop:
                    break

            if ctx.should_stop:
                break

        ctx.current_given = self._RE_SPACE.sub(" ", current_given).strip()
        ctx.current_reference = self._RE_SPACE.sub(" ", "\n".join(new_ref_lines)).strip()
        ctx.resolved_reference = self._RE_SPACE.sub(" ", "\n".join(resolved_ref_lines)).strip()

    def _process_line(self, thesis: str, current_given: str) -> Tuple[List[ErrorDetail], str, str, str]:
        errors: List[ErrorDetail] = []

        substituted, invalid_param_ids = self._substitute_params(thesis)
        for p_id in invalid_param_ids:
            errors.append(ErrorDetail(type=ErrorType.PARAM_PREGRADE_FAILED, expected=p_id))

        substituted_clean, literals = self._protect_literal_square_brackets(substituted)

        cursor = 0
        pattern = ""
        specs: List[Tuple[RangeSpec, str]] = []

        for match in self._RE_RANGE.finditer(substituted_clean):
            start, end = match.span()
            if any(start >= l_start and end <= l_end for l_start, l_end in literals):
                continue
            pattern += re.escape(substituted_clean[cursor:start])
            raw = match.group(1)
            spec = RangeSpec.from_raw(raw)
            specs.append((spec, raw))
            pattern += spec.regex_fragment()
            cursor = end

        pattern += re.escape(substituted_clean[cursor:])

        if not specs:
            norm_sub = self._normalize(substituted_clean)
            resolved_thesis = self._RE_LITERAL_ESCAPE.sub(r'[\1]', substituted_clean)
            if norm_sub not in self._normalize(current_given):
                errors.append(ErrorDetail(type=ErrorType.LITERAL_MISSING, expected=substituted_clean))
            return errors, current_given, thesis, resolved_thesis

        matcher = self._compile_pattern(pattern)
        match_obj = matcher.search(current_given)

        if match_obj:
            idx_counter = [1]
            def replace_range(m: re.Match) -> str:
                val = match_obj.group(idx_counter[0])
                idx_counter[0] += 1
                return val
            resolved_thesis = self._RE_RANGE.sub(replace_range, substituted_clean)
        else:
            resolved_thesis = self._RE_RANGE.sub(r'\1', substituted_clean)
            errors.append(ErrorDetail(type=ErrorType.REGEX_NO_MATCH, expected=substituted_clean))

        resolved_thesis = self._RE_LITERAL_ESCAPE.sub(r'[\1]', resolved_thesis)

        if not match_obj:
            return errors, current_given, thesis, resolved_thesis

        for idx, (spec, raw) in enumerate(specs, start=1):
            value = match_obj.group(idx)
            if not spec.match(value):
                errors.append(ErrorDetail(
                    type=ErrorType.PARAM_MISMATCH,
                    expected=raw,
                    actual=value
                ))

        given_chars = list(current_given)
        for idx in range(1, len(specs) + 1):
            start, end = match_obj.span(idx)
            for i in range(start, end):
                given_chars[i] = ' '
        new_given = "".join(given_chars)

        new_ref = self._RE_PRESENCE_CHECK.sub(' ', thesis)
        new_ref = self._RE_LITERAL_ESCAPE.sub(r'[\1]', new_ref)

        return errors, new_given, new_ref, resolved_thesis

    def _substitute_params(self, line: str) -> Tuple[str, List[str]]:
        invalid_params: List[str] = []

        def replace(match: re.Match) -> str:
            name = match.group(1)
            param = self._parameters.get(name)
            if not param:
                return match.group(0)

            data_dict = param.data or {}
            inner_data = data_dict.get("data") or data_dict
            text_value = inner_data.get("text", "")

            pre_grade_dict = getattr(param, "pre_grade", None) or data_dict.get("pre_grade") or {}
            score = pre_grade_dict.get("score", 1)

            if score == 0:
                invalid_params.append(name)

            return text_value or match.group(0)

        substituted = self._RE_PARAM.sub(replace, line)
        return substituted, invalid_params

    def _protect_literal_square_brackets(self, text: str) -> Tuple[str, List[Tuple[int, int]]]:
        result = ""
        protected_ranges: List[Tuple[int, int]] = []
        last = 0

        for match in self._RE_LITERAL_ESCAPE.finditer(text):
            start, end = match.span()
            content = match.group(1)
            result += text[last:start] + "[" + content + "]"
            protected_ranges.append((len(result) - len(content) - 2, len(result)))
            last = end

        result += text[last:]
        return result, protected_ranges

    @staticmethod
    @lru_cache(maxsize=256)
    def _normalize(text: str) -> str:
        return ParametrizedAnswerGrader._RE_SPACE.sub(" ", text.lower()).strip()

    @staticmethod
    @lru_cache(maxsize=512)
    def _compile_pattern(pattern: str) -> re.Pattern:
        return re.compile(pattern, re.IGNORECASE)