import re
from functools import lru_cache
from typing import List, Tuple, Union


class RangeSpec:
    _RE_RANGE_FLOAT = re.compile(r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*-\s*([+-]?\d+(?:[.,]\d+)?)\s*$")
    _RE_FLOAT = re.compile(r"^[+-]?\d+[.,]\d+$")
    _RE_INT = re.compile(r"^[+-]?\d+$")

    def __init__(self, raw: str):
        self.raw = raw.strip()
        self.parts: List[Union[int, float, str, Tuple[Union[int, float], Union[int, float]]]] = []

        for token in (tok.strip() for tok in self.raw.split("|") if tok.strip()):
            if match := self._RE_RANGE_FLOAT.fullmatch(token):
                start_str = match.group(1).replace(',', '.')
                end_str = match.group(2).replace(',', '.')

                if '.' in start_str or '.' in end_str:
                    start, end = sorted((float(start_str), float(end_str)))
                else:
                    start, end = sorted((int(start_str), int(end_str)))
                self.parts.append((start, end))
            elif self._RE_INT.fullmatch(token):
                self.parts.append(int(token))
            elif self._RE_FLOAT.fullmatch(token):
                self.parts.append(float(token.replace(',', '.')))
            else:
                self.parts.append(token)

    @classmethod
    @lru_cache(maxsize=256)
    def from_raw(cls, raw: str) -> "RangeSpec":
        return cls(raw)

    @property
    def is_numeric(self) -> bool:
        return all(not isinstance(part, str) for part in self.parts)

    @property
    def is_float(self) -> bool:
        for part in self.parts:
            if isinstance(part, float):
                return True
            if isinstance(part, tuple) and any(isinstance(subpart, float) for subpart in part):
                return True
        return False

    @property
    def is_mixed(self) -> bool:
        has_str = any(isinstance(part, str) for part in self.parts)
        has_num = any(isinstance(part, (int, float, tuple)) for part in self.parts)
        return has_str and has_num

    @property
    def values(self) -> List[Union[str, int, float]]:
        result: List[Union[str, int, float]] = []
        for part in self.parts:
            if isinstance(part, tuple):
                result.append(f"{part[0]}..{part[1]}")
            else:
                result.append(part)
        return result

    def regex_fragment(self) -> str:
        if self.is_numeric:
            return r"(-?\d+(?:[.,]\d+)?)"
        return r"(\S+(?:\s+\S+)*)"

    def match(self, text: str) -> bool:
        stripped = text.strip()
        num_str = stripped.replace(',', '.')
        is_number_like = re.fullmatch(r"^-?\d+(?:\.\d+)?$", num_str)

        if is_number_like:
            try:
                value = float(num_str)
                for part in self.parts:
                    if isinstance(part, tuple):
                        start, end = part
                        if start <= value <= end:
                            if not self.is_float and not value.is_integer():
                                continue
                            return True
                    elif isinstance(part, (int, float)):
                        if value == part:
                            return True
            except ValueError:
                pass

        lowered = stripped.lower()
        return any(part.lower() == lowered for part in self.parts if isinstance(part, str))