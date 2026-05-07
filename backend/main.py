import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi_hypermodel import HyperModel
from dotenv import load_dotenv

from answer.handlers import register_answer_error_handlers
from config.settings import TOOL_CONF
from core.db_handler import register_db_error_handler
from core.halhypermodel import HALHyperModel
from core.ttl_cache import RedisCache
from lti.handlers import register_lti_error_handlers
from report.handlers import register_report_error_handlers
from template.handlers import register_template_error_handlers

load_dotenv()

from config.auth import auth
from core.db import close_db

from lti.router import router as lti_router
from template.router import router as template_router
from files.router import router as file_router
from report.router import router as report_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    HALHyperModel.init_app(app)
    HyperModel.init_app(app)
    app.state.cache = RedisCache()
    app.state.tool_conf = TOOL_CONF
    yield
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
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

def run_prod():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)