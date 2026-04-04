import logging
from contextlib import asynccontextmanager

import uvicorn
from authx.exceptions import JWTDecodeError
from fastapi import FastAPI
from fastapi_hypermodel import HyperModel
from pylti1p3.tool_config import ToolConfJsonFile
from dotenv import load_dotenv
from starlette.requests import Request
from starlette.responses import JSONResponse

from core.halhypermodel import HALHyperModel

load_dotenv()

from config.main import LTI_CONFIG_FILE_PATH
from config.auth import auth
from core.db import close_db

from lti.router import router as lti_router
from template.router import router as template_router
from files.router import router as file_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    HALHyperModel.init_app(app)
    HyperModel.init_app(app)
    app.state.tool_conf = ToolConfJsonFile(LTI_CONFIG_FILE_PATH)
    yield
    await close_db()
    logging.shutdown()

app = FastAPI(lifespan=lifespan)
app.include_router(lti_router, prefix="/api/v1")
app.include_router(template_router, prefix="/api/v1")
app.include_router(file_router, prefix="/files/v1")

auth.handle_errors(app)
@app.exception_handler(JWTDecodeError)
async def jwt_decode_error_handler(request: Request, exc: JWTDecodeError):
    return JSONResponse(
        status_code=401,
        content={
            "detail": "Token is invalid or expired",
            "error_type": "JWTDecodeError",
        },
    )

def run_dev():
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

def run_prod():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)