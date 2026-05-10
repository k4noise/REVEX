import uuid
from typing import Optional

from report.schemas.report_status import ReportStatus


class AccessDeniedException(Exception):
    def __init__(self, reason: str):
        super().__init__(f"Доступ запрещен: {reason}")


class RoleAccessDeniedException(AccessDeniedException):
    def __init__(self):
        super().__init__("недопустимые права")


class NotOwnerAccessDeniedException(AccessDeniedException):
    def __init__(self):
        super().__init__("пользователь не является автором")


class InvalidCourseAccessDeniedException(AccessDeniedException):
    def __init__(self):
        super().__init__("шаблон или отчет другого курса")


class ReportStateAccessDeniedException(AccessDeniedException):
    def __init__(self, status: ReportStatus):
        super().__init__(f"отчет недоступен для инструктора - статус {status.value}")


class EntityNotFoundException(Exception):
    def __init__(self, name: str, id: Optional[uuid.UUID]):
        super().__init__(f"{name} с id {id} не найден")


class ReportNotFoundException(EntityNotFoundException):
    def __init__(self, report_id: Optional[uuid.UUID] = None):
        super().__init__("Отчет", report_id)