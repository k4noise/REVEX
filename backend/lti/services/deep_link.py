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

    DEEP_LINK_SETTINGS_CLAIM = (
        "https://purl.imsglobal.org/spec/lti-dl/claim/deep_linking_settings"
    )

    def __init__(self, session: AsyncSession):
        self.session = session
        self.redis = RedisCache()

    def _key(self, state: str) -> str:
        return f"{self.STATE_PREFIX}{state}"

    def _decode_state(self, raw: Any) -> dict:
        if raw is None:
            raise LtiLaunchException("Deep link state не найден или истёк")

        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")

        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except json.JSONDecodeError as e:
                raise LtiLaunchException("Deep link state повреждён") from e

        if isinstance(raw, dict):
            return raw

        raise LtiLaunchException(
            f"Некорректный формат deep link state: {type(raw).__name__}"
        )

    def _load_state(self, state: str) -> dict:
        raw = self.redis.get(self._key(state))
        return self._decode_state(raw)

    def _get_deep_link_settings(self, message_launch: FastAPIMessageLaunch) -> dict:
        launch_data = message_launch.get_launch_data()
        settings = launch_data.get(self.DEEP_LINK_SETTINGS_CLAIM)

        if not settings:
            raise LtiLaunchException("В launch отсутствует deep_linking_settings")

        if not isinstance(settings, dict):
            raise LtiLaunchException("Некорректный формат deep_linking_settings")

        return settings

    async def save_state(self, message_launch: FastAPIMessageLaunch) -> str:
        settings = self._get_deep_link_settings(message_launch)
        state = uuid.uuid4().hex

        payload = {
            "launch_id": message_launch.get_launch_id(),
            "accept_multiple": bool(settings.get("accept_multiple", False)),
            "title": settings.get("title"),
            "text": settings.get("text"),
            "data": settings.get("data"),
        }

        self.redis.set(
            self._key(state),
            json.dumps(payload),
            ttl=self.STATE_TTL,
        )
        return state

    async def get_templates_for_picker(self) -> list[dict]:
        result = await self.session.execute(
            select(Template)
            .where(Template.is_draft.is_(False))
            .order_by(Template.name.asc())
        )
        templates = result.scalars().all()

        return [
            {
                "id": str(template.id),
                "name": template.name,
                "max_score": template.max_score,
            }
            for template in templates
        ]

    async def create_response_html(
            self,
            state: str,
            template_ids: list[uuid.UUID],
    ) -> str:
        state_data = self._load_state(state)

        if len(template_ids) > 1 and not state_data.get("accept_multiple", False):
            raise LtiLaunchException("Платформа не разрешает множественный выбор")

        message_launch = _get_message_launch_from_cache(state_data["launch_id"])
        deep_link = message_launch.get_deep_link()

        resources: list[DeepLinkResource] = []

        if template_ids:
            templates = await self._load_templates_by_ids(template_ids)
            resources = [self._build_resource(template) for template in templates]

        return deep_link.output_response_form(resources)

    async def _load_templates_by_ids(
            self,
            template_ids: list[uuid.UUID],
    ) -> list[Template]:
        result = await self.session.execute(
            select(Template).where(
                Template.id.in_(template_ids),
                Template.is_draft.is_(False),
            )
        )
        templates = result.scalars().all()

        by_id = {template.id: template for template in templates}
        missing = [template_id for template_id in template_ids if template_id not in by_id]
        if missing:
            raise LtiLaunchException("Некоторые шаблоны не найдены")

        return [by_id[template_id] for template_id in template_ids]

    def _build_resource(self, template: Template) -> DeepLinkResource:
        public_backend_url = os.getenv("PUBLIC_BACKEND_URL")
        if not public_backend_url:
            raise LtiLaunchException("PUBLIC_BACKEND_URL не настроен")

        launch_url = f"{public_backend_url.rstrip('/')}/api/v1/lti/launch"

        resource = DeepLinkResource()
        resource.set_url(launch_url) \
            .set_title(template.name) \
            .set_custom_params({
            "template_id": str(template.id),
        })

        return resource