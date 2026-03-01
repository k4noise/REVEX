import redis
import pickle
import threading


class RedisCache:
    """Синхронный потокобезопасный кеш с вытеснением старых записей на основе Redis"""

    def __init__(self, host='localhost', port=6379, db=0):
        self._redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=False,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            try:
                serialized = self._redis.get(key)
                if serialized is None:
                    return None

                value, original_ttl = pickle.loads(serialized)
                self._redis.expire(key, original_ttl)
                return value
            except Exception:
                return None

    def set(self, key, value, ttl):
        with self._lock:
            try:
                serialized = pickle.dumps((value, ttl))
                self._redis.set(key, serialized, ex=ttl)
            except Exception:
                return

    def delete(self, key):
        with self._lock:
            try:
                self._redis.delete(key)
            except Exception:
                return

    def clear(self):
        with self._lock:
            try:
                self._redis.flushdb()
            except Exception:
                return

    def get_cache_size(self):
        with self._lock:
            try:
                return self._redis.dbsize()
            except Exception:
                return 0

    def get_connection(self):
        return self._redis

    def set_many(self, data, ttl):
        with self._lock:
            try:
                pipeline = self._redis.pipeline()

                for key, value in data.items():
                    serialized_value = pickle.dumps((value, ttl))
                    pipeline.set(key, serialized_value, ex=ttl)

                pipeline.execute()

            except Exception:
                return

    def set_many_if_not_present(self, data, ttl):
        with self._lock:
            try:
                exists_pipeline = self._redis.pipeline()
                for key in data.keys():
                    exists_pipeline.exists(key)
                exists_results = exists_pipeline.execute()

                if any(exists_results):
                    return False

                pipeline = self._redis.pipeline()
                for key, value in data.items():
                    serialized_value = pickle.dumps((value, ttl))
                    pipeline.set(key, serialized_value, ex=ttl, nx=True)

                results = pipeline.execute()
                return all(results)

            except Exception:
                return False

    def get_many(self, keys):
        with self._lock:
            try:
                serialized_values = self._redis.mget(keys)
                result = {}
                expire_pipeline = self._redis.pipeline()

                for key, serialized in zip(keys, serialized_values):
                    if serialized is None:
                        continue

                    try:
                        value, original_ttl = pickle.loads(serialized)
                        result[key] = value
                        expire_pipeline.expire(key, original_ttl)
                    except (pickle.UnpicklingError, ValueError, TypeError) as e:
                        try:
                            self._redis.delete(key)
                        except redis.RedisError:
                            return

                if expire_pipeline:
                    expire_pipeline.execute()

                return result

            except Exception:
                return {}
