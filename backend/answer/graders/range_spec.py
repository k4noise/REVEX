import re
from functools import lru_cache
from typing import List, Tuple, Union


NumericValue = Union[int, float]
RangeTuple = Tuple[NumericValue, NumericValue]
SpecPart = Union[int, float, str, RangeTuple]


class RangeSpec:
    PATTERN_NUMERIC_RANGE = re.compile(
        r'^\s*([+-]?\d+(?:[.,]\d+)?)\s*-\s*([+-]?\d+(?:[.,]\d+)?)\s*$'
    )
    PATTERN_FLOAT = re.compile(r'^[+-]?\d+[.,]\d+$')
    PATTERN_INT = re.compile(r'^[+-]?\d+$')
    PATTERN_DASHES = re.compile(r'[\u2010\u2011\u2012\u2013\u2014\u2212]')
    PATTERN_DASH_SPACES = re.compile(r'\s*-\s*')

    def __init__(self, raw: str):
        normalized = self.PATTERN_DASHES.sub('-', raw)
        normalized = self.PATTERN_DASH_SPACES.sub('-', normalized)
        self.raw = normalized.strip()
        self.parts: List[SpecPart] = []

        for token in (tok.strip() for tok in self.raw.split('|') if tok.strip()):
            self.parts.append(self._parse_token(token))

    def _parse_token(self, token: str) -> SpecPart:
        range_match = self.PATTERN_NUMERIC_RANGE.fullmatch(token)
        if range_match:
            start_str = range_match.group(1).replace(',', '.')
            end_str = range_match.group(2).replace(',', '.')

            if '.' in start_str or '.' in end_str:
                start, end = float(start_str), float(end_str)
            else:
                start, end = int(start_str), int(end_str)

            return (min(start, end), max(start, end))

        if self.PATTERN_INT.fullmatch(token):
            return int(token)

        if self.PATTERN_FLOAT.fullmatch(token):
            return float(token.replace(',', '.'))

        return token

    @classmethod
    @lru_cache(maxsize=256)
    def from_raw(cls, raw: str) -> "RangeSpec":
        return cls(raw)

    def get_fallback_value(self) -> str:
        if not self.parts:
            return "1"

        first_part = self.parts[0]

        if isinstance(first_part, tuple):
            return str(int(first_part[0]))

        if isinstance(first_part, (int, float)):
            return str(int(first_part))

        if isinstance(first_part, str):
            try:
                return str(int(float(first_part)))
            except ValueError:
                return "1"

        return "1"

    @property
    def is_numeric(self) -> bool:
        return all(not isinstance(part, str) for part in self.parts)

    @property
    def is_float(self) -> bool:
        for part in self.parts:
            if isinstance(part, float):
                return True
            if isinstance(part, tuple):
                if isinstance(part[0], float) or isinstance(part[1], float):
                    return True
        return False

    def regex_fragment(self) -> str:
        if self.is_numeric:
            return r'(-?\d+(?:[.,]\d+)?)'
        return r'(\S+(?:\s+\S+)*)'

    def match(self, text: str) -> bool:
        stripped = text.strip()
        normalized_number = stripped.replace(',', '.')

        if re.fullmatch(r'^-?\d+(?:\.\d+)?$', normalized_number):
            try:
                numeric_value = float(normalized_number)

                for part in self.parts:
                    if isinstance(part, tuple):
                        range_start, range_end = part
                        if range_start <= numeric_value <= range_end:
                            if not self.is_float and not numeric_value.is_integer():
                                continue
                            return True
                    elif isinstance(part, (int, float)):
                        if numeric_value == part:
                            return True
            except ValueError:
                pass

        lowered = stripped.lower()
        return any(
            isinstance(part, str) and part.lower() == lowered
            for part in self.parts
        )