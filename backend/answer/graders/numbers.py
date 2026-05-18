import re
from collections import Counter

from answer.graders.base import BaseGrader
from answer.schemas import GradingContext, ErrorDetail, ErrorType


class NumbersGrader(BaseGrader):
    PATTERN_NUMBER = re.compile(r'-?\d+(?:[.,]\d+)?')
    PATTERN_WHITESPACE = re.compile(r'\s+')

    def process(self, context: GradingContext) -> None:
        if not context.resolved_reference:
            return

        reference_normalized = context.resolved_reference.replace(',', '.')
        given_normalized = context.remaining_given.replace(',', '.')

        reference_numbers = Counter(self.PATTERN_NUMBER.findall(reference_normalized))
        given_numbers = Counter(self.PATTERN_NUMBER.findall(given_normalized))

        for already_checked in context.numbers_checked_by_params:
            normalized = already_checked.replace(',', '.')
            if normalized in reference_numbers:
                del reference_numbers[normalized]

        for number, required_count in reference_numbers.items():
            if given_numbers.get(number, 0) < required_count:
                context.add_error(ErrorDetail(
                    type=ErrorType.MISSING_NUMBER,
                    expected=number
                ))

        context.remaining_reference = self._strip_numbers(reference_normalized)
        context.remaining_given = self._strip_numbers(given_normalized)

    def _strip_numbers(self, text: str) -> str:
        stripped = self.PATTERN_NUMBER.sub(' ', text)
        return self.PATTERN_WHITESPACE.sub(' ', stripped).strip()