class LtiBaseException(Exception):
    pass


class LisNotSupportedException(LtiBaseException):
    def __init__(self, name: str):
        super().__init__(f"Служба {name} недоступна")


class NrpsNotSupportedException(LisNotSupportedException):
    def __init__(self):
        super().__init__("имен и ролей (NRPS)")


class AgsNotSupportedException(LisNotSupportedException):
    def __init__(self):
        super().__init__("оценок (AGS)")


class LtiLoginException(LtiBaseException):
    def __init__(self, detail: str):
        super().__init__(detail)


class LtiLaunchException(LtiBaseException):
    def __init__(self, detail: str):
        super().__init__(detail)


class LtiTokenRefreshException(LtiBaseException):
    def __init__(self, detail: str):
        super().__init__(detail)


class LtiUserNotFoundException(LtiBaseException):
    def __init__(self, user_id: int):
        super().__init__(f"LTI-пользователь с id {user_id} не найден")
        self.user_id = user_id