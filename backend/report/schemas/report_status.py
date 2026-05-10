import enum

from sqlalchemy import TypeDecorator, String


class ReportStatus(str, enum.Enum):
    CREATED = "created"
    SAVED = "saved"
    SUBMITTED = "submitted"
    GRADED = "graded"


class ReportStatusType(TypeDecorator):
    impl = String
    cache_ok = True

    def __init__(self):
        super().__init__()
        self.enum_class = ReportStatus

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return value.value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return self.enum_class(value.lower())
        except ValueError:
            possible_values = [e.value for e in self.enum_class]
            raise ValueError(
                f"Значение '{value}' из базы данных (после приведения к нижнему регистру '{value.lower()}') "
                f"не соответствует ни одному ожидаемому значению в {self.enum_class.__name__}. "
                f"Ожидаемые значения: {possible_values}."
            )
