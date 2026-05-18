import re
from functools import lru_cache

from rapidfuzz import fuzz

from answer.graders.base import BaseGrader
from answer.schemas import GradingContext


class FuzzyGrader(BaseGrader):
    PATTERN_WORD = re.compile(r'[A-Za-zА-Яа-я0-9_.:/-]+')

    def process(self, context: GradingContext) -> None:
        reference = context.resolved_reference
        if not reference or len(reference) > self.config.max_fuzz_reference_length:
            return

        reference_words = self._extract_words(context.remaining_reference)
        given_words = self._extract_words(context.remaining_given)

        if not reference_words:
            context.is_perfect_match = True
            return

        if self._is_match(reference_words, given_words):
            context.is_perfect_match = True

    def _is_match(
            self,
            reference_words: tuple[str, ...],
            given_words: tuple[str, ...]
    ) -> bool:
        if reference_words == given_words:
            return True

        if self._is_prefix_match(reference_words, given_words):
            return True

        if self._is_fuzzy_subsequence(reference_words, given_words):
            return True

        if self._is_fuzzy_subsequence(given_words, reference_words):
            return True

        return False

    def _is_prefix_match(
            self,
            first_seq: tuple[str, ...],
            second_seq: tuple[str, ...]
    ) -> bool:
        shorter, longer = sorted([first_seq, second_seq], key=len)
        return all(
            longer_word.startswith(shorter_word)
            for shorter_word, longer_word in zip(shorter, longer)
        )

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
        return tuple(FuzzyGrader.PATTERN_WORD.findall(text.lower()))