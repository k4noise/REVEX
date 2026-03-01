import os
from pylti1p3.tool_config import ToolConfJsonFile

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_PROJECT_DIR = os.path.dirname(os.path.dirname(CONFIG_DIR))
LTI_CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, 'lti_config.json')
TOOL_CONF = ToolConfJsonFile(LTI_CONFIG_FILE_PATH)

