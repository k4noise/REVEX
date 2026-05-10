from core.auth.user_model import User
from template.exceptions import InvalidCourseAccessDeniedException, InvalidTransitionException
from template.models.template import Template


class TemplateAccessVerifier:
    def __init__(self, template: Template):
        self.template = template

    def is_valid_course(self, user: User) -> "TemplateAccessVerifier":
        if self.template.course_id != user.course_id:
            raise InvalidCourseAccessDeniedException()
        return self

    def can_publish(self) -> "TemplateAccessVerifier":
        if not self.template.is_draft:
            raise InvalidTransitionException()
        return self
