from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
from starlette import status
import structlog

from answer.exceptions import AnswerPatchException, AnswerNotFoundException

logger = structlog.get_logger(__name__)


def register_answer_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AnswerPatchException)
    async def answer_patch_error_handler(
            request: Request,
            exc: AnswerPatchException,
    ):
        logger.warning(
            "answer.error.patch",
            detail=str(exc),
            path=str(request.url.path),
            method=request.method,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc), "error_type": "answer_patch_error"},
        )

    @app.exception_handler(AnswerNotFoundException)
    async def answer_not_found_handler(
            request: Request,
            exc: AnswerNotFoundException,
    ):
        logger.warning(
            "answer.error.not_found",
            detail=str(exc),
            path=str(request.url.path),
            method=request.method,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc), "error_type": "answer_not_found"},
        )