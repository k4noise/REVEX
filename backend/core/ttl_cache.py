import json
import os
from datetime import timedelta
from typing import Any, Dict, List, Optional

import redis


class RedisCache:
    def __init__(
            self,
            redis_url: Optional[str] = None,
            host: Optional[str] = None,
            port: Optional[int] = None,
            db: Optional[int] = None,
            password: Optional[str] = None,
            username: Optional[str] = None,
    ):
        redis_url = redis_url or os.getenv("REDIS_URL")

        if redis_url:
            self._redis = redis.Redis.from_url(
                redis_url,
                decode_responses=False,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
        else:
            self._redis = redis.Redis(
                host=host or os.getenv("REDIS_HOST", "localhost"),
                port=port or int(os.getenv("REDIS_PORT", "6379")),
                db=db if db is not None else int(os.getenv("REDIS_DB", "0")),
                username=username or os.getenv("REDIS_USERNAME") or None,
                password=password or os.getenv("REDIS_PASSWORD") or None,
                decode_responses=False,
                socket_timeout=5,
                socket_connect_timeout=5,
            )

        self._redis.ping()

    def get(self, key: str) -> Any:
        try:
            data = self._redis.get(key)
            if not data:
                return None
            return json.loads(data)
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl: timedelta | int):
        try:
            ttl_seconds = ttl.total_seconds() if isinstance(ttl, timedelta) else ttl
            if ttl_seconds <= 0:
                return
            serialized = json.dumps(value, default=str)
            self._redis.set(key, serialized, ex=int(ttl_seconds))
        except Exception:
            pass

    def delete(self, key: str):
        try:
            self._redis.delete(key)
        except Exception:
            pass

    def ttl(self, key: str) -> int | None:
        try:
            ttl = self._redis.ttl(key)
            if ttl is None or ttl < 0:
                return None
            return int(ttl)
        except Exception:
            return None

    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        try:
            values = self._redis.mget(keys)
            result = {}
            for key, val in zip(keys, values):
                if val is None:
                    continue
                try:
                    result[key] = json.loads(val)
                except Exception:
                    self.delete(key)
            return result
        except Exception:
            return {}

    def set_many_if_not_present(
            self,
            data: Dict[str, Any],
            ttl: timedelta | int,
    ) -> bool:
        try:
            ttl_seconds = ttl.total_seconds() if isinstance(ttl, timedelta) else ttl
            if ttl_seconds <= 0:
                return False

            keys = list(data.keys())

            while True:
                try:
                    with self._redis.pipeline() as pipe:
                        pipe.watch(*keys)
                        existing = pipe.mget(keys)

                        if any(value is not None for value in existing):
                            pipe.reset()
                            return False

                        pipe.multi()
                        for key, value in data.items():
                            serialized = json.dumps(value, default=str)
                            pipe.set(key, serialized, ex=int(ttl_seconds), nx=True)

                        results = pipe.execute()
                        return all(result is True for result in results)
                except redis.WatchError:
                    continue
        except Exception:
            return False

    def clear(self):
        try:
            cursor = 0
            while True:
                cursor, keys = self._redis.scan(cursor=cursor, count=500)
                if keys:
                    self._redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception:
            pass