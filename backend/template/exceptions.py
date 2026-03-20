import uuid


class EntityNotFoundException(Exception):
    """Исключение, возникающее при отсутствии сущности в БД"""

    def __init__(self, name: str, id: uuid.UUID):
        super().__init__(f"{name} с id {id} не найден")


class TemplateNotFoundException(EntityNotFoundException):
    """Исключение, возникающее при попытке доступа к несуществующему шаблону"""

    def __init__(self, template_id: uuid.UUID):
        super().__init__("Шаблон", template_id)

class InvalidActionException(Exception):
    """Исключение, возникающее при выполнении действия, приводящего к конфликту"""

    def __init__(self, reason: str):
        super().__init__(f"Конфликт действия: {reason}")


class InvalidTransitionException(InvalidActionException):
    """Исключение, возникающее при попытке перехода в запрещенное состояние"""

    def __init__(self):
        super().__init__("недопустимый переход состояния шаблона")


class AccessDeniedException(Exception):
    """Исключение, возникающее при отсутствии доступа к ресурсу"""

    def __init__(self, reason: str):
        super().__init__(f"Доступ запрещен: {reason}")



class InvalidCourseAccessDeniedException(AccessDeniedException):
    """Исключение, возникающее при попытке доступа к сущности другого курса"""

    def __init__(self):
        super().__init__("шаблон или отчет другого курса")