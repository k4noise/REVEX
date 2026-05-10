from pylti1p3.cookie import CookieService
from pylti1p3.oidc_login import OIDCLogin
from pylti1p3.request import Request
from pylti1p3.session import SessionService
from pylti1p3.tool_config import ToolConfAbstract

from lti.services.cache import FastAPICacheDataStorage
from lti.services.cookie import FastAPICookieService
from lti.services.redirect import FastAPIRedirect
from lti.services.session import FastAPISessionService


class FastAPIOIDCLogin(OIDCLogin):
    def __init__(
            self,
            request: Request,
            tool_config: ToolConfAbstract,
            session_service: SessionService=None,
            cookie_service: CookieService=None,
            launch_data_storage: FastAPICacheDataStorage=None,
    ):
        cookie_service = (
            cookie_service if cookie_service else FastAPICookieService(request)
        )
        session_service = (
            session_service if session_service else FastAPISessionService(request)
        )
        super().__init__(
            request, tool_config, session_service, cookie_service, launch_data_storage
        )

    def get_redirect(self, url):
        return FastAPIRedirect(url, self._cookie_service)
