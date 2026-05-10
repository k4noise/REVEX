from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
from starlette import status
import structlog

from .exceptions import (
    TemplateNotFoundException,
    TemplatePatchException,
    InvalidCourseAccessDeniedException,
    InvalidTransitionException,
    InvalidActionException, TemplateParseException
)

logger = structlog.get_logger(__name__)


def register_template_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(TemplateNotFoundException)
    async def template_not_found_handler(
            request: Request,
            exc: TemplateNotFoundException,
    ):
        logger.warning(
            "template.error.not_found",
            detail=str(exc),
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": str(exc),
                "error_type": "template_not_found",
            },
        )

    @app.exception_handler(InvalidCourseAccessDeniedException)
    async def template_access_denied_handler(
            request: Request,
            exc: InvalidCourseAccessDeniedException,
    ):
        logger.warning(
            "template.error.access_denied",
            detail=str(exc),
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "detail": str(exc),
                "error_type": "template_access_denied",
            },
        )

    @app.exception_handler(InvalidTransitionException)
    async def template_invalid_transition_handler(
            request: Request,
            exc: InvalidTransitionException,
    ):
        logger.info(
            "template.error.invalid_transition",
            detail=str(exc),
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": str(exc),
                "error_type": "invalid_template_state",
            },
        )

    @app.exception_handler(TemplatePatchException)
    async def template_patch_error_handler(
            request: Request,
            exc: TemplatePatchException,
    ):
        logger.warning(
            "template.error.invalid_patch",
            detail=str(exc),
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": str(exc),
                "error_type": "invalid_template_patch",
            },
        )

    @app.exception_handler(InvalidActionException)
    async def template_invalid_action_handler(
            request: Request,
            exc: InvalidActionException,
    ):
        logger.info(
            "template.error.invalid_action",
            detail=str(exc),
            path=str(request.url.path),
            method=request.method,
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc), "error_type": "invalid_action"},
        )

    @app.exception_handler(TemplateParseException)
    async def template_parse_error_handler(
            request: Request,
            exc: TemplateParseException,
    ):
        logger.warning(
            "template.error.parse",
            detail=str(exc),
            path=str(request.url.path),
            method=request.method,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": str(exc),
                "error_type": "template_parse_error",
            },
        )