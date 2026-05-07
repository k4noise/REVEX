from typing import Callable, Any
import os

from redis import Redis
from rq import Queue
import structlog

logger = structlog.get_logger(__name__)


class BackgroundTaskService:
    def __init__(self, redis_url: str | None = None, default_timeout: int = 180):
        env_redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_url = redis_url if redis_url is not None else env_redis_url
        self.default_timeout = default_timeout
        self.queue: Queue | None = None
        self._init_queue()

    def _init_queue(self) -> None:
        try:
            conn = Redis.from_url(self.redis_url, socket_connect_timeout=3)
            self.queue = Queue(
                connection=conn,
                default_timeout=self.default_timeout,
            )
            logger.info(
                "BackgroundTaskService подключён к очереди",
                redis_url=self.redis_url,
            )
        except Exception as e:
            logger.error(
                "Не удалось подключиться к Redis",
                redis_url=self.redis_url,
                error=str(e),
            )
            self.queue = None

    def enqueue(self, func: Callable, *args: Any, **kwargs: Any):
        if not self.queue:
            logger.warning(
                "Очередь RQ недоступна, задача пропущена",
                redis_url=self.redis_url,
            )
            return None

        try:
            job = self.queue.enqueue(
                func,
                *args,
                **kwargs,
                failure_ttl=3600,
                result_ttl=1800,
            )
            logger.info(
                "Задача добавлена в очередь",
                job_id=job.id,
                function=func.__name__,
                queue_name=self.queue.name,
            )
            return job
        except Exception as e:
            logger.error(
                "Ошибка постановки задачи в RQ",
                function=func.__name__,
                queue_name=self.queue.name,
                error=str(e),
            )
            return None