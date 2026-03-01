from fastapi import Response
from fastapi.responses import RedirectResponse, HTMLResponse
from pylti1p3.redirect import Redirect


class FastAPIRedirect(Redirect):
    """
    Сервис для создания редиректов
    """
    _location = None
    _cookie_service = None

    def __init__(self, location, cookie_service=None):
        super().__init__()
        self._location = location
        self._cookie_service = cookie_service

    def do_redirect(self):
        return self._process_response(RedirectResponse(url=self._location, status_code=302))

    def do_js_redirect(self):
        return self._process_response(
            HTMLResponse(
                content=f'<script type="text/javascript">window.location="{self._location}";</script>',
                status_code=200,
            )
        )

    def set_redirect_url(self, location):
        self._location = location

    def get_redirect_url(self):
        return self._location

    def _process_response(self, response: Response):
        """
        Добавляет куки к ответу, если они были заданы
        """
        if self._cookie_service:
            self._cookie_service.update_response(response)
        return response
