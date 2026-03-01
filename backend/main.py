import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from pylti1p3.tool_config import ToolConfJsonFile
from dotenv import load_dotenv

load_dotenv()

from config.main import LTI_CONFIG_FILE_PATH
from config.auth import auth
from core.db import close_db

from lti.router import router as lti_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.tool_conf = ToolConfJsonFile(LTI_CONFIG_FILE_PATH)
    auth.handle_errors(app)
    yield
    await close_db()
    logging.shutdown()

app = FastAPI(lifespan=lifespan)
app.include_router(lti_router, prefix="/api/v1")

def run_dev():
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

def run_prod():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)