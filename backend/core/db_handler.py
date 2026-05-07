from fastapi import FastAPI, Request
from starlette.responses import JSONResponse
from starlette import status
import structlog
from sqlalchemy.exc import SQLAlchemyError

logger = structlog.get_logger(__name__)


def register_db_error_handler(app: FastAPI) -> None:
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(
            request: Request,
            exc: SQLAlchemyError,
    ):
        logger.error(
            "db.error",
            path=str(request.url.path),
            method=request.method,
            error=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Ошибка доступа к данным",
                "error_type": "database_error",
            },
        )