from contextlib import suppress
from typing import Optional

import structlog
from pydantic import ValidationError
from pylti1p3.message_launch import MessageLaunch


from lti.exceptions import NrpsNotSupportedException
from lti.schemas import NrpsUser
from lti.services.course import CourseService


class NrpsService:
    """Получение данных пользователя из службы ролей и имен LTI NRPS"""

    def __init__(self, message_launch: MessageLaunch, logger = structlog.get_logger(__name__)):
        if not message_launch.has_nrps():
            raise NrpsNotSupportedException()
        self.message_launch = message_launch
        self.logger = logger
        self._members_map: Optional[dict[str, NrpsUser]] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def get_user_by_id(self, user_id: str) -> Optional[NrpsUser]:
        """Получить данные из NRPS по идентификатору пользователя"""
        self._ensure_members_loaded()
        return self._members_map.get(user_id)

    def _ensure_members_loaded(self) -> None:
        """Загружает данные, если они еще не были загружены"""
        if self._members_map is None:
            members = self.message_launch.get_nrps().get_members()
            self.logger.warning(f"Получен доступ к данным NRPS в курсе {CourseService(self.message_launch).name}")

            self._members_map = {}
            for user_data in members:
                with suppress(ValidationError):
                    self._members_map[user_data.get("user_id")] = NrpsUser.model_validate(user_data)
