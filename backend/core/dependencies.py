from functools import lru_cache

from starlette.requests import Request

from core.background_service import BackgroundTaskService
from core.ttl_cache import RedisCache
from files.services.hybrid_storage import HybridStorage


def get_cache(request: Request) -> RedisCache:
    return request.app.state.cache


@lru_cache(maxsize=1)
def get_file_storage() -> HybridStorage:
    return HybridStorage()


def get_background_task_service() -> BackgroundTaskService:
    return BackgroundTaskService()