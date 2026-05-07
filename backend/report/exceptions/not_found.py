import uuid
from typing import Optional


class EntityNotFoundException(Exception):
    def __init__(self, name: str, id: uuid.UUID):
        super().__init__(f"{name} с id {id} не найден")



class ReportNotFoundException(EntityNotFoundException):
    def __init__(self, report_id: Optional[uuid.UUID] = None):
        super().__init__("Отчет", report_id)
