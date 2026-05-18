import re
from functools import lru_cache

from rapidfuzz import fuzz

from answer.graders.base import BaseGrader
from answer.schemas import GradingContext, ErrorDetail, ErrorType


class StrictMatchGrader(BaseGrader):
    PATTERN_WORD = re.compile(r'[A-Za-zА-Яа-я0-9_.:/-]+')

    def process(self, context: GradingContext) -> None:
        if not context.resolved_reference:
            return

        reference_lines = [
            line.strip()
            for line in context.resolved_reference.splitlines()
            if line.strip() and line.strip() != '*'
        ]

        given_words = self._extract_words(context.raw_given)

        all_lines_matched = True
        for line in reference_lines:
            line_words = self._extract_words(line)
            if not line_words:
                continue

            if not self._is_fuzzy_subsequence(line_words, given_words):
                context.add_error(ErrorDetail(
                    type=ErrorType.KEYWORD_MISMATCH,
                    expected=line
                ))
                all_lines_matched = False

        if all_lines_matched:
            context.is_perfect_match = True

    def _is_fuzzy_subsequence(
            self,
            needle: tuple[str, ...],
            haystack: tuple[str, ...]
    ) -> bool:
        if not needle:
            return True
        if len(needle) > len(haystack):
            return False

        haystack_index = 0
        for needle_word in needle:
            found = False
            while haystack_index < len(haystack):
                if self._words_match(needle_word, haystack[haystack_index]):
                    haystack_index += 1
                    found = True
                    break
                haystack_index += 1
            if not found:
                return False
        return True

    def _words_match(self, first_word: str, second_word: str) -> bool:
        if first_word.startswith(second_word) or second_word.startswith(first_word):
            return True
        return fuzz.ratio(first_word, second_word) >= self.config.fuzzy_word_similarity

    @staticmethod
    @lru_cache(maxsize=256)
    def _extract_words(text: str) -> tuple[str, ...]:
        return tuple(StrictMatchGrader.PATTERN_WORD.findall(text.lower()))