from typing import Sequence, Optional

from pylti1p3.message_launch import MessageLaunch

from core.user_model import UserRole
from lti.services.nrps import NrpsService


class UserService:
    """
    Сервис обработки данных пользователя из данных запуска
    """

    def __init__(self, message_launch: MessageLaunch, nrps_service: NrpsService | None = None):
        self.message_launch = message_launch
        self.launch_data = message_launch.get_launch_data()
        self._nrps_service = nrps_service

    @property
    def id(self) -> str:
        return self.launch_data.get("sub")

    @property
    def roles(self) -> Sequence[UserRole]:
        return [
            role
            for role, checker in [
                (UserRole.TEACHER, self.message_launch.check_teacher_access),
                (UserRole.ASSISTANT, self.message_launch.check_teaching_assistant_access),
                (UserRole.STUDENT, self.message_launch.check_student_access),
            ]
            if checker()
        ]

    @property
    def full_name(self) -> Optional[str]:
        if name := self.launch_data.get("name"):
            return name
        if self._nrps_service:
            if user := self._nrps_service.get_user_data(self.id):
                return user.name
        return None
