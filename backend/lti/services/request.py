from urllib.parse import parse_qs

from fastapi import Request as FastAPIReq
from pylti1p3.request import Request


class FastAPIRequest(Request):
    """
    Сервис-обертка для запросов FastAPI.
    Для извлечения параметров запроса нужно вызвать асинхронный метод parse_request
    """
    def __init__(self, request: FastAPIReq = None):
        super().__init__()
        self.query_params = None
        self.body = None
        self._request = request

    async def parse_request(self):
        """Извлекает все необходимые данные из запроса"""
        self.query_params = self._request.query_params
        data = await self._request.body()
        self.body = parse_qs(data.decode('utf-8'))

    @property
    def session(self):
        return self._request.session

    def is_secure(self) -> bool:
        return self._request.url.scheme == "https"

    def get_param(self, key):
        if self.body and self.body.get(key, [None]):
            return self.body.get(key, [None])[0]
        elif self.query_params:
            return self.query_params.get(key, None)
        return None

    def get_cookie(self, key):
        return self._request.cookies.get(key)

    def get_tool(self):
        return self._request.app.state.tool_conf
