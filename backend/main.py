import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi_hypermodel import HyperModel

from answer.handlers import register_answer_error_handlers
from config.settings import REDIS_URL, TOOL_CONF
from config.auth import auth
from core.db import close_db
from core.db_handler import register_db_error_handler
from core.halhypermodel import HALHyperModel
from core.ttl_cache import RedisCache
from files.router import router as file_router
from lti.handlers import register_lti_error_handlers
from lti.router import router as lti_router
from report.handlers import register_report_error_handlers
from report.router import router as report_router
from template.handlers import register_template_error_handlers
from template.router import router as template_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    HALHyperModel.init_app(app)
    HyperModel.init_app(app)
    app.state.cache = RedisCache(redis_url=REDIS_URL)
    app.state.tool_conf = TOOL_CONF
    try:
        yield
    finally:
        await close_db()
        logging.shutdown()


app = FastAPI(lifespan=lifespan)

app.include_router(lti_router, prefix="/api/v1")
app.include_router(template_router, prefix="/api/v1")
app.include_router(report_router, prefix="/api/v1")
app.include_router(file_router, prefix="/files/v1")

auth.handle_errors(app)
register_db_error_handler(app)
register_lti_error_handlers(app)
register_template_error_handlers(app)
register_report_error_handlers(app)
register_answer_error_handlers(app)


def run_dev():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


def run_prod():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)