import os
from pathlib import Path

from dotenv import load_dotenv
from pylti1p3.tool_config import ToolConfJsonFile

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
FILES_STORAGE_DIR = BASE_DIR / "images"
LTI_CONFIG_PATH = BASE_DIR / "config" / "lti_config.json"
ONNX_MODEL_DIR = BASE_DIR.parent / "assets" / "rubert-tiny2"
USER_IMAGE_PREFIX = "content"

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

if not LTI_CONFIG_PATH.exists():
    raise FileNotFoundError(f"LTI config not found: {LTI_CONFIG_PATH}")

TOOL_CONF = ToolConfJsonFile(str(LTI_CONFIG_PATH))