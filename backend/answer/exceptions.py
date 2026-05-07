import uuid
from typing import Optional


class AnswerPatchException(Exception):
    def __init__(self, reason: str):
        super().__init__(f"Ошибка обновления ответов: {reason}")


class AnswerNotFoundException(Exception):
    def __init__(self, answer_id: Optional[uuid.UUID] = None):
        msg = "Ответ не найден"
        if answer_id:
            msg = f"{msg}: id {answer_id}"
        super().__init__(msg)