from typing import Callable, Any
import os

from redis import Redis
from rq import Queue
import structlog

logger = structlog.get_logger(__name__)


class BackgroundTaskService:
    def __init__(
            self,
            redis_url: str | None = None,
            default_timeout: int = 180,
            queue_name: str | None = None,
    ):
        env_redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        env_queue_name = os.getenv("RQ_QUEUE")

        self.redis_url = redis_url if redis_url is not None else env_redis_url

        raw_queue_name = queue_name if queue_name is not None else env_queue_name
        if raw_queue_name in (None, "", "None", "null", "NULL"):
            raw_queue_name = "default"

        self.queue_name = raw_queue_name
        self.default_timeout = default_timeout
        self.queue: Queue | None = None
        self._init_queue()

    def _init_queue(self) -> None:
        try:
            conn = Redis.from_url(
                self.redis_url,
                decode_responses=False,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            conn.ping()

            self.queue = Queue(
                name=self.queue_name,
                connection=conn,
                default_timeout=self.default_timeout,
            )

            logger.info(
                "BackgroundTaskService connected",
                redis_url=self.redis_url,
                queue_name=self.queue_name,
            )
        except Exception as e:
            logger.error(
                "BackgroundTaskService redis init failed",
                redis_url=self.redis_url,
                queue_name=self.queue_name,
                error=str(e),
            )
            self.queue = None

    def enqueue(self, func: Callable, *args: Any, **kwargs: Any):
        if not self.queue:
            logger.warning(
                "Background queue unavailable, task skipped",
                redis_url=self.redis_url,
                queue_name=self.queue_name,
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
                "Background task enqueued",
                job_id=job.id,
                function=func.__name__,
                queue_name=self.queue.name,
                redis_url=self.redis_url,
            )
            return job
        except Exception as e:
            logger.error(
                "Background task enqueue failed",
                function=func.__name__,
                queue_name=self.queue.name,
                redis_url=self.redis_url,
                error=str(e),
            )
            return None