from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
from starlette import status
import structlog

from report.exceptions import (
    ReportNotFoundException,
    RoleAccessDeniedException,
    NotOwnerAccessDeniedException,
    InvalidCourseAccessDeniedException,
    ReportStateAccessDeniedException,
)

logger = structlog.get_logger(__name__)


def register_report_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ReportNotFoundException)
    async def report_not_found_handler(
            request: Request,
            exc: ReportNotFoundException,
    ):
        logger.warning(
            "report.error.not_found",
            detail=str(exc),
            path=str(request.url.path),
            method=request.method,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc), "error_type": "report_not_found"},
        )

    @app.exception_handler(RoleAccessDeniedException)
    @app.exception_handler(NotOwnerAccessDeniedException)
    @app.exception_handler(InvalidCourseAccessDeniedException)
    async def report_access_denied_handler(
            request: Request,
            exc: Exception,
    ):
        logger.warning(
            "report.error.access_denied",
            exc_class=exc.__class__.__name__,
            detail=str(exc),
            path=str(request.url.path),
            method=request.method,
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc), "error_type": "report_access_denied"},
        )

    @app.exception_handler(ReportStateAccessDeniedException)
    async def report_state_access_denied_handler(
            request: Request,
            exc: ReportStateAccessDeniedException,
    ):
        logger.warning(
            "report.error.state_access_denied",
            detail=str(exc),
            path=str(request.url.path),
            method=request.method,
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc), "error_type": "report_state_access_denied"},
        )