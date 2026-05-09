import enum

from pydantic import BaseModel, field_validator


class UserRole(enum.Enum):
    STUDENT = "student"
    ASSISTANT = "assistant"
    TEACHER = "teacher"


class User(BaseModel):
    id: str
    roles: list[UserRole]
    launch_id: str
    course_id: str
    accepted_policy: bool = False

    def is_teacher(self) -> bool:
        return UserRole.TEACHER in self.roles

    def is_instructor(self) -> bool:
        return UserRole.TEACHER in self.roles or UserRole.ASSISTANT in self.roles

    def is_student(self) -> bool:
        return UserRole.STUDENT in self.roles

    @field_validator("roles", mode="before")
    @classmethod
    def convert_roles_to_enum(cls, raw_roles):
        if raw_roles is None:
            return []

        result: list[UserRole] = []
        for role in raw_roles:
            if isinstance(role, str):
                result.append(UserRole(role))
            else:
                result.append(role)
        return result