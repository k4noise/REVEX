import enum
from typing import List

from pydantic import BaseModel, field_validator


class UserRole(enum.Enum):
    """Роли пользователя"""
    STUDENT = 'student'
    ASSISTANT = 'assistant'
    TEACHER = 'teacher'


class User(BaseModel):
    """Модель данных пользователя, получаемая из JWT-токена"""
    id: str
    roles: List[UserRole]
    launch_id: str
    course_id: str
    accepted_policy: bool = False

    def is_teacher(self) -> bool:
        return UserRole.TEACHER in self.roles

    def is_instructor(self) -> bool:
        return UserRole.TEACHER in self.roles or UserRole.ASSISTANT in self.roles

    def is_student(self) -> bool:
        return UserRole.STUDENT in self.roles

    @field_validator('roles', mode='before')
    def convert_roles_to_enum(cls, raw_roles: List[str | UserRole]) -> List[UserRole]:
        """Конвертирует строку с ролью в соответствующее значение UserRole"""
        result = []
        for role in raw_roles:
            if isinstance(role, str):
                result.append(UserRole(role))
            else:
                result.append(role)
        return result
