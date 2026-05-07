import uuid


class EntityNotFoundException(Exception):
    def __init__(self, name: str, id: uuid.UUID):
        super().__init__(f"{name} с id {id} не найден")


class TemplateNotFoundException(EntityNotFoundException):
    def __init__(self, template_id: uuid.UUID):
        super().__init__("Шаблон", template_id)


class InvalidActionException(Exception):
    def __init__(self, reason: str):
        super().__init__(f"Конфликт действия: {reason}")


class InvalidTransitionException(InvalidActionException):
    def __init__(self):
        super().__init__("недопустимый переход состояния шаблона")


class AccessDeniedException(Exception):
    def __init__(self, reason: str):
        super().__init__(f"Доступ запрещен: {reason}")


class InvalidCourseAccessDeniedException(AccessDeniedException):
    def __init__(self):
        super().__init__("шаблон или отчет другого курса")


class TemplateElementNotFoundException(EntityNotFoundException):
    def __init__(self, element_id: uuid.UUID):
        super().__init__("Элемент шаблона", element_id)


class TemplatePatchException(Exception):
    def __init__(self, reason: str):
        super().__init__(f"Некорректный патч шаблона: {reason}")

class TemplateParseException(Exception):
    def __init__(self, filename: str | None = None):
        if filename:
            msg = f"Не удалось распарсить файл шаблона: {filename}"
        else:
            msg = "Не удалось распарсить файл шаблона"
        super().__init__(msg)
        self.filename = filename