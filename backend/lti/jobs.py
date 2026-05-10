import asyncio
import json
import uuid
from typing import Any, Optional

import structlog
from pylti1p3.cookie import CookieService
from pylti1p3.exception import LtiException
from pylti1p3.request import Request as LtiRequest
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import TOOL_CONF
from core.db import AsyncSessionLocal
from core.ttl_cache import RedisCache
from lti.services.ags import AgsService
from lti.services.cache import FastAPICacheDataStorage
from lti.services.launch import LaunchService
from lti.services.message_launch import FastAPIMessageLaunch
from template.models.template import Template
from template.schemas.template import TemplateStructure

logger = structlog.get_logger(__name__)


class SilentCookieService(CookieService):
    def __init__(self, request=None):
        self._request = request

    def get_cookie(self, name: str) -> Optional[str]:
        return None

    def set_cookie(self, name: str, value, exp: int = 3600) -> None:
        return None

class DummyLtiRequest(LtiRequest):
    def __init__(self, tool_conf):
        super().__init__()
        self._tool_conf = tool_conf

    def get_param(self, key):
        return None

    def get_cookie(self, key):
        return None

    def is_secure(self):
        return True

    def get_tool(self):
        return self._tool_conf


def _normalize_launch_data(value: Any) -> dict:
    if value is None:
        raise LtiException("Launch data is empty")

    if isinstance(value, bytes):
        value = value.decode("utf-8")

    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as e:
            raise LtiException("Launch data in Redis is not valid JSON") from e

    if not isinstance(value, dict):
        raise LtiException(
            f"Launch data has unexpected type: {type(value).__name__}"
        )

    return value


def _load_launch_data_from_cache(launch_id: str) -> dict:
    cache_storage = FastAPICacheDataStorage(RedisCache())
    raw = cache_storage.get_launch_data(launch_id)

    if not raw:
        raise LtiException(
            f"Launch data not found in cache for launch_id={launch_id}"
        )

    return _normalize_launch_data(raw)


def _restore_message_launch_from_data(
        launch_id: str,
        launch_data: dict,
) -> FastAPIMessageLaunch:
    dummy_request = DummyLtiRequest(TOOL_CONF)

    message_launch = FastAPIMessageLaunch(
        dummy_request,
        TOOL_CONF,
        cookie_service=SilentCookieService(dummy_request),
    )

    return (
        message_launch
        .set_launch_id(launch_id)
        .set_auto_validation(False)
        .set_jwt({"body": launch_data})
        .set_restored()
        .validate_registration()
    )


def _get_message_launch_from_cache(launch_id: str) -> FastAPIMessageLaunch:
    launch_data = _load_launch_data_from_cache(launch_id)
    return _restore_message_launch_from_data(launch_id, launch_data)


async def _load_template(
        session: AsyncSession,
        template_id: uuid.UUID,
) -> Optional[Template]:
    return await session.get(Template, template_id)


def _build_template_structure(template: Template) -> TemplateStructure:
    return TemplateStructure(
        id=template.id,
        name=template.name,
        max_score=template.max_score,
        is_draft=template.is_draft,
        elements=[],
    )



def ags_create_lineitem_job(launch_id: str, template_id_str: str) -> None:
    template_id = uuid.UUID(template_id_str)
    asyncio.run(_ags_create_lineitem_async(launch_id, template_id))


async def _ags_create_lineitem_async(
        launch_id: str,
        template_id: uuid.UUID,
) -> None:
    logger.info(
        "ags_create_lineitem.start",
        launch_id=launch_id,
        template_id=str(template_id),
    )

    async with AsyncSessionLocal() as session:  # type: AsyncSession
        try:
            template = await _load_template(session, template_id)
            if not template:
                logger.warning(
                    "ags_create_lineitem.template_not_found",
                    template_id=str(template_id),
                )
                return

            message_launch = _get_message_launch_from_cache(launch_id)
            ags = AgsService(message_launch)

            dto = _build_template_structure(template)
            ags.create_lineitem(dto)

            logger.info(
                "ags_create_lineitem.ok",
                launch_id=launch_id,
                template_id=str(template_id),
            )
        except Exception:
            logger.exception(
                "ags_create_lineitem.failed",
                launch_id=launch_id,
                template_id=str(template_id),
            )


def ags_delete_lineitem_job(launch_id: str, template_id_str: str) -> None:
    template_id = uuid.UUID(template_id_str)
    asyncio.run(_ags_delete_lineitem_async(launch_id, template_id))


async def _ags_delete_lineitem_async(
        launch_id: str,
        template_id: uuid.UUID,
) -> None:
    logger.info(
        "ags_delete_lineitem.start",
        launch_id=launch_id,
        template_id=str(template_id),
    )

    try:
        message_launch = _get_message_launch_from_cache(launch_id)
        ags = AgsService(message_launch)

        ags.delete_lineitem(template_id)

        logger.info(
            "ags_delete_lineitem.ok",
            launch_id=launch_id,
            template_id=str(template_id),
        )
    except Exception:
        logger.exception(
            "ags_delete_lineitem.failed",
            launch_id=launch_id,
            template_id=str(template_id),
        )



def ags_set_grade_job(
        launch_id: str,
        template_id_str: str,
        user_id: str,
        score: float,
) -> None:
    template_id = uuid.UUID(template_id_str)
    asyncio.run(_ags_set_grade_async(launch_id, template_id, user_id, score))


async def _ags_set_grade_async(
        launch_id: str,
        template_id: uuid.UUID,
        user_id: str,
        score: float,
) -> None:
    logger.info(
        "ags_set_grade.start",
        launch_id=launch_id,
        template_id=str(template_id),
        user_id=user_id,
        score=score,
    )

    async with AsyncSessionLocal() as session:  # type: AsyncSession
        try:
            template = await _load_template(session, template_id)
            if not template:
                logger.warning(
                    "ags_set_grade.template_not_found",
                    template_id=str(template_id),
                )
                return

            message_launch = _get_message_launch_from_cache(launch_id)
            ags = AgsService(message_launch)

            dto = _build_template_structure(template)
            lti_user_id = await LaunchService(session).get_user_bind(user_id)

            if not lti_user_id:
                logger.warning(
                    "ags_set_grade.user_bind_not_found",
                    user_id=user_id,
                )
                return

            ags.set_grade(dto, lti_user_id, score)

            logger.info(
                "ags_set_grade.ok",
                launch_id=launch_id,
                template_id=str(template_id),
                user_id=user_id,
                score=score,
            )
        except Exception:
            logger.exception(
                "ags_set_grade.failed",
                launch_id=launch_id,
                template_id=str(template_id),
                user_id=user_id,
                score=score,
            )