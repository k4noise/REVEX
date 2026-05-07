
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
    def __init__(self, status: "ReportStatus"):
        super().__init__(f"отчет недоступен для инструктора - статус {str(status)}")
