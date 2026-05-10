import structlog
from authx.exceptions import JWTDecodeError
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
from starlette import status

from lti.exceptions import (
    LtiLoginException,
    LtiLaunchException,
    LtiTokenRefreshException,
    LtiUserNotFoundException,
    LisNotSupportedException,
)

logger = structlog.get_logger(__name__)


def register_lti_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(LtiLoginException)
    async def lti_login_error_handler(
            request: Request,
            exc: LtiLoginException,
    ):
        logger.warning(
            "lti.error.login",
            detail=str(exc),
            path=str(request.url.path),
            method=request.method,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc), "error_type": "lti_login_error"},
        )

    @app.exception_handler(LtiLaunchException)
    async def lti_launch_error_handler(
            request: Request,
            exc: LtiLaunchException,
    ):
        logger.warning(
            "lti.error.launch",
            detail=str(exc),
            path=str(request.url.path),
            method=request.method,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc), "error_type": "lti_launch_error"},
        )

    @app.exception_handler(LtiTokenRefreshException)
    async def lti_token_refresh_error_handler(
            request: Request,
            exc: LtiTokenRefreshException,
    ):
        logger.warning(
            "lti.error.token_refresh",
            detail=str(exc),
            path=str(request.url.path),
            method=request.method,
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": str(exc), "error_type": "lti_token_refresh_error"},
        )

    @app.exception_handler(LtiUserNotFoundException)
    async def lti_user_not_found_handler(
            request: Request,
            exc: LtiUserNotFoundException,
    ):
        logger.warning(
            "lti.error.user_not_found",
            detail=str(exc),
            user_id=exc.user_id,
            path=str(request.url.path),
            method=request.method,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc), "error_type": "lti_user_not_found"},
        )

    @app.exception_handler(LisNotSupportedException)
    async def lti_lis_not_supported_handler(
            request: Request,
            exc: LisNotSupportedException,
    ):
        logger.warning(
            "lti.error.lis_not_supported",
            detail=str(exc),
            path=str(request.url.path),
            method=request.method,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc), "error_type": "lti_lis_not_supported"},
        )

    @app.exception_handler(JWTDecodeError)
    async def jwt_decode_error_handler(request: Request, exc: JWTDecodeError):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": "Token is invalid or expired",
                "error_type": "JWTDecodeError",
            },
        )