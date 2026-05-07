from starlette.requests import Request

from core.background_service import BackgroundTaskService
from files.services.hybrid_storage import HybridStorage
from core.ttl_cache import RedisCache


def get_cache(request: Request) -> RedisCache:
    return request.app.state.cache


def get_file_storage():
    return HybridStorage()

def get_background_task_service() -> BackgroundTaskService:
    return BackgroundTaskService()