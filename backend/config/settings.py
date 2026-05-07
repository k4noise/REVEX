from pylti1p3.tool_config import ToolConfJsonFile

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FILES_STORAGE_DIR = BASE_DIR / "images"
LTI_CONFIG_PATH = BASE_DIR / "config" / "lti_config.json"
ONNX_MODEL_DIR = BASE_DIR.parent / "assets" / "rubert-tiny2"
USER_IMAGE_PREFIX = "content"

TOOL_CONF = ToolConfJsonFile(str(LTI_CONFIG_PATH))

