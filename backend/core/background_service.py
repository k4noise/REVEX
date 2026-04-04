from redis import Redis
from rq import Queue
import structlog

logger = structlog.get_logger(__name__)

class BackgroundTaskService:
    """Обертка над Redis Queue (RQ) для фоновых задач"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        try:
            self.redis_conn = Redis.from_url(redis_url)
            self.queue = Queue(connection=self.redis_conn)
            logger.info("BackgroundTaskService успешно подключен к Redis")
        except Exception as e:
            logger.error(f"Ошибка подключения к Redis: {e}")
            self.queue = None

    def enqueue(self, func, *args, **kwargs):
        """Безопасное добавление задачи в очередь"""
        if not self.queue:
            logger.warning("Очередь недоступна, задача пропущена")
            return None

        try:
            # Отправляем саму функцию и аргументы (без замыканий/closures!)
            job = self.queue.enqueue(func, *args, **kwargs)
            logger.debug(f"Задача {job.id} добавлена в очередь")
            return job
        except Exception as e:
            logger.error(f"Не удалось добавить задачу в RQ: {e}")
            return None