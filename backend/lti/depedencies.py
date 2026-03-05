from fastapi import Request

from lti.services.cache import FastAPICacheDataStorage
from lti.services.request import FastAPIRequest
from ttl_cache import RedisCache

ttl_cache = RedisCache()

async def get_lti_request(request: Request) -> FastAPIRequest:
    adapter = FastAPIRequest(request)
    await adapter.parse_request()
    return adapter


async def get_lti_cache_storage() -> FastAPICacheDataStorage:
    return FastAPICacheDataStorage(ttl_cache)
