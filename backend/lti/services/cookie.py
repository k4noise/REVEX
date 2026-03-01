from fastapi import Response
from pylti1p3.cookie import CookieService

from lti.services.request import FastAPIRequest


class FastAPICookieService(CookieService):
    _request: FastAPIRequest
    _cookie_data_to_set: dict

    def __init__(self, request: FastAPIRequest = None):
        self._cookie_data_to_set = {}
        self._request = request

    def get_cookie(self, name: str) -> str:
        return self._request.get_cookie(self._get_key(name))

    def set_cookie(self, name: str, value: str, exp: int = 3600):
        self._cookie_data_to_set[self._get_key(name)] = {"value": value, "exp": exp}

    def _get_key(self, key: str) -> str:
        """Возвращает ключ с префиксом"""
        return f"{self._cookie_prefix}-{key}"

    def update_response(self, response: Response) -> Response:
        """Модифицирует ответ, добавляя в него куки"""
        for key, cookie_data in self._cookie_data_to_set.items():
            cookie_kwargs = dict(
                key=key,
                value=cookie_data["value"],
                max_age=cookie_data["exp"],
                path="/",
                httponly=True,
                samesite=None
            )
            response.set_cookie(**cookie_kwargs)
        return response
