import json
import redis
from datetime import timedelta
from typing import Any, Dict, List


class RedisCache:
    def __init__(self, host='localhost', port=6379, db=0):
        self._redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=False,
            socket_timeout=5,
            socket_connect_timeout=5
        )

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
            serialized = json.dumps(value, default=str)
            self._redis.set(key, serialized, ex=int(ttl_seconds))
        except Exception:
            pass

    def delete(self, key: str):
        try:
            self._redis.delete(key)
        except Exception:
            pass

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

    def set_many_if_not_present(self, data: Dict[str, Any], ttl: timedelta | int) -> bool:
        try:
            ttl_seconds = ttl.total_seconds() if isinstance(ttl, timedelta) else ttl
            pipe = self._redis.pipeline()

            for key in data.keys():
                pipe.exists(key)

            exists = pipe.execute()
            if any(exists):
                return False

            pipe = self._redis.pipeline()
            for key, value in data.items():
                serialized = json.dumps(value, default=str)
                pipe.set(key, serialized, ex=int(ttl_seconds), nx=True)

            results = pipe.execute()
            return all(r is True for r in results)
        except Exception:
            return False

    def clear(self):
        try:
            self._redis.flushdb()
        except Exception:
            pass