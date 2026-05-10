import re
from collections import Counter
from functools import lru_cache

from rapidfuzz import fuzz
from answer.schemas import GradingContext, ErrorDetail, ErrorType


class FixedAnswerGrader:
    RE_WORDS = re.compile(r"[A-Za-z0-9_.:/-]+")
    RE_DIGITS = re.compile(r'-?\d+(?:[.,]\d+)?')
    RE_SPACE = re.compile(r"\s+")

    DEFAULT_SIMILARITY_THRESHOLD = 80
    MAX_PROCESSABLE_LENGTH = 35

    def process_numbers(self, ctx: GradingContext) -> None:
        if not ctx.current_reference:
            return

        ref_str = ctx.current_reference.replace(',', '.')
        given_str = ctx.current_given.replace(',', '.')

        ref_digits = Counter(self.RE_DIGITS.findall(ref_str))
        given_digits = Counter(self.RE_DIGITS.findall(given_str))

        for num, count in ref_digits.items():
            if given_digits.get(num, 0) < count:
                ctx.add_error(ErrorDetail(type=ErrorType.MISSING_NUMBER, expected=num))
                if ctx.should_stop:
                    return

        ctx.current_reference = self.RE_SPACE.sub(" ", self.RE_DIGITS.sub(" ", ref_str)).strip()
        ctx.current_given = self.RE_SPACE.sub(" ", self.RE_DIGITS.sub(" ", given_str)).strip()

    def process_fuzz(self, ctx: GradingContext) -> None:
        if not ctx.current_reference or len(ctx.current_reference) > self.MAX_PROCESSABLE_LENGTH:
            return

        given_words = self._extract_words(ctx.current_given)
        ref_words = self._extract_words(ctx.current_reference)

        if not ref_words:
            ctx.is_perfect_match = True
            return

        if given_words == ref_words or self._is_strict_prefix(given_words, ref_words) or \
                self._is_fuzzy_subsequence(ref_words, given_words) or self._is_fuzzy_subsequence(given_words, ref_words):
            ctx.is_perfect_match = True

    def process_strict_log(self, ctx: GradingContext) -> None:
        if not ctx.resolved_reference:
            return

        ref_lines = [line.strip() for line in ctx.resolved_reference.splitlines() if line.strip() and line.strip() != '*']
        given_words = self._extract_words(ctx.original_given)

        for line in ref_lines:
            line_words = self._extract_words(line)
            if not line_words:
                continue

            if not self._is_fuzzy_subsequence(line_words, given_words):
                ctx.add_error(ErrorDetail(type=ErrorType.KEYWORD_MISMATCH, expected=line))
                ctx.final_score = 0.0
                if ctx.should_stop:
                    return

        ctx.is_perfect_match = True

    @staticmethod
    @lru_cache(maxsize=128)
    def _extract_words(text: str) -> tuple[str, ...]:
        return tuple(FixedAnswerGrader.RE_WORDS.findall(text.lower()))

    def _words_match(self, word1: str, word2: str) -> bool:
        return (word1.startswith(word2) or
                word2.startswith(word1) or
                fuzz.ratio(word1, word2) >= self.DEFAULT_SIMILARITY_THRESHOLD)

    @staticmethod
    def _is_strict_prefix(shorter_seq: tuple[str, ...], longer_seq: tuple[str, ...]) -> bool:
        if len(shorter_seq) > len(longer_seq):
            return False
        return all(long_w.startswith(short_w) for short_w, long_w in zip(shorter_seq, longer_seq))

    def _is_fuzzy_subsequence(self, subsequence: tuple[str, ...], main_sequence: tuple[str, ...]) -> bool:
        main_iter = iter(main_sequence)
        for sub_word in subsequence:
            if not any(self._words_match(sub_word, main_word) for main_word in main_iter):
                return False
        return True