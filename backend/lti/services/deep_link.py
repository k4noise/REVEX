import json
import os
import uuid
from typing import Any
from pylti1p3.deep_link_resource import DeepLinkResource
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.ttl_cache import RedisCache
from lti.exceptions import LtiLaunchException
from lti.jobs import _get_message_launch_from_cache
from lti.services.message_launch import FastAPIMessageLaunch
from template.models.template import Template

class DeepLinkService:
    STATE_PREFIX = "lti:deep-link:state:"
    STATE_TTL = 15 * 60
    DEEP_LINK_SETTINGS_CLAIM = "https://purl.imsglobal.org/spec/lti-dl/claim/deep_linking_settings"

    def __init__(self, session: AsyncSession):
        self.session = session
        self.redis = RedisCache()

    def _key(self, state: str) -> str:
        return f"{self.STATE_PREFIX}{state}"

    def _decode_state(self, raw: Any) -> dict:
        if raw is None: raise LtiLaunchException("Deep link state не найден")
        if isinstance(raw, bytes): raw = raw.decode("utf-8")
        if isinstance(raw, str): return json.loads(raw)
        if isinstance(raw, dict): return raw
        raise LtiLaunchException("Некорректный формат state")

    def _load_state(self, state: str) -> dict:
        raw = self.redis.get(self._key(state))
        return self._decode_state(raw)

    def _get_deep_link_settings(self, message_launch: FastAPIMessageLaunch) -> dict:
        launch_data = message_launch.get_launch_data()
        settings = launch_data.get(self.DEEP_LINK_SETTINGS_CLAIM)
        if not isinstance(settings, dict): raise LtiLaunchException("Некорректный deep_linking_settings")
        return settings

    async def save_state(self, message_launch: FastAPIMessageLaunch) -> str:
        settings = self._get_deep_link_settings(message_launch)
        state = uuid.uuid4().hex
        payload = {
            "launch_id": message_launch.get_launch_id(),
            "accept_multiple": False,
            "title": settings.get("title"),
            "text": settings.get("text"),
            "data": settings.get("data"),
        }
        self.redis.set(self._key(state), json.dumps(payload), ttl=self.STATE_TTL)
        return state

    async def get_templates_for_picker(self, course_id: int) -> list[dict]:
        result = await self.session.execute(
            select(Template)
            .where(Template.is_draft.is_(False), Template.course_id == course_id)
            .order_by(Template.name.asc())
        )
        templates = result.scalars().all()
        return [{"id": str(t.id), "name": t.name, "max_score": t.max_score} for t in templates]

    async def create_response_html(self, state: str, template_ids: list[uuid.UUID]) -> str:
        state_data = self._load_state(state)
        message_launch = _get_message_launch_from_cache(state_data["launch_id"])
        deep_link = message_launch.get_deep_link()
        resources = []
        if template_ids:
            templates = await self._load_templates_by_ids(template_ids)
            resources = [self._build_resource(t) for t in templates]
        return deep_link.output_response_form(resources)

    async def _load_templates_by_ids(self, template_ids: list[uuid.UUID]) -> list[Template]:
        result = await self.session.execute(
            select(Template).where(Template.id.in_(template_ids), Template.is_draft.is_(False))
        )
        templates = result.scalars().all()
        by_id = {t.id: t for t in templates}
        if any(tid not in by_id for tid in template_ids):
            raise LtiLaunchException("Шаблоны не найдены")
        return [by_id[tid] for tid in template_ids]

    def _build_resource(self, template: Template) -> DeepLinkResource:
        url = os.getenv("PUBLIC_BACKEND_URL")
        if not url: raise LtiLaunchException("PUBLIC_BACKEND_URL не настроен")
        launch_url = f"{url.rstrip('/')}/api/v1/lti/launch"
        resource = DeepLinkResource()
        resource.set_url(launch_url).set_title(template.name).set_custom_params({"template_id": str(template.id)})
        return resource