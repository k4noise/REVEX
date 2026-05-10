from typing import Literal, Optional, Sequence

from pydantic import BaseModel


class NrpsUser(BaseModel):
    """Минимально необходимые данные из NRPS о пользователе"""
    status: Literal["Active", "Inactive", "Deleted"]
    name: Optional[str] = None
    roles: Sequence[str]
