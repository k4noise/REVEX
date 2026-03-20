from typing import Generator

from fastapi import Request, Depends

from config.main import TOOL_CONF
from core.auth.depedency import get_user
from core.auth.user_model import User
from lti.services.ags import AgsService
from lti.services.cache import FastAPICacheDataStorage
from lti.services.course import CourseService
from lti.services.message_launch import FastAPIMessageLaunch
from lti.services.nrps import NrpsService
from lti.services.request import FastAPIRequest
from ttl_cache import RedisCache

ttl_cache = RedisCache()

async def get_lti_request(request: Request) -> FastAPIRequest:
    adapter = FastAPIRequest(request)
    await adapter.parse_request()
    return adapter


async def get_lti_cache_storage() -> FastAPICacheDataStorage:
    return FastAPICacheDataStorage(ttl_cache)


def get_message_launch(
        request: Request,
        user: User = Depends(get_user),
        cache_storage: FastAPICacheDataStorage = Depends(get_lti_cache_storage)
) -> FastAPIMessageLaunch:
    return FastAPIMessageLaunch.from_cache(
        user.launch_id,
        FastAPIRequest(request),
        TOOL_CONF,
        launch_data_storage=cache_storage
    )

def get_nrps_service(
        message_launch: FastAPIMessageLaunch = Depends(get_message_launch)
) -> Generator[NrpsService, None, None]:
    with NrpsService(message_launch) as nrps:
        yield nrps


def get_ags_service(
        message_launch: FastAPIMessageLaunch = Depends(get_message_launch),
) -> AgsService:
    return AgsService(message_launch)


def get_course_service(
        message_launch: FastAPIMessageLaunch = Depends(get_message_launch)
) -> CourseService:
    return CourseService(message_launch)