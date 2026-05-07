import uuid
from typing import Sequence, Any

from sqlalchemy import insert, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from template.exceptions import TemplatePatchException
from template.models.template_element import TemplateElement

logger = structlog.get_logger(__name__)


class TemplateElementRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_create_raw(self, payloads: list[dict[str, Any]]) -> None:
        if not payloads:
            return

        await self.session.execute(
            insert(TemplateElement),
            payloads,
        )

    async def bulk_update_from_map(
            self,
            template_id: uuid.UUID,
            updates_map: dict[uuid.UUID, dict[str, Any]],
    ) -> None:
        if not updates_map:
            return

        ids = list(updates_map.keys())
        stmt = select(TemplateElement).where(
            TemplateElement.id.in_(ids),
            TemplateElement.template_id == template_id,
            )
        result = await self.session.execute(stmt)
        elements = result.scalars().all()

        found_ids = {el.id for el in elements}
        missing_ids = set(ids) - found_ids
        if missing_ids:
            logger.warning(
                "template_elements.update.missing_ids",
                template_id=str(template_id),
                missing_ids=[str(i) for i in missing_ids],
            )
            raise TemplatePatchException(
                f"Попытка обновить элементы, не принадлежащие шаблону {template_id}: {missing_ids}"
            )

        for el in elements:
            data = updates_map[el.id]

            if "properties" in data:
                el.properties = (el.properties or {}) | data.pop("properties")

            for key, value in data.items():
                if hasattr(el, key):
                    setattr(el, key, value)

        await self.session.flush()

    async def bulk_delete(self, template_id: uuid.UUID, ids: list[uuid.UUID]) -> None:
        if not ids:
            return

        stmt = delete(TemplateElement).where(
            TemplateElement.template_id == template_id,
            TemplateElement.id.in_(ids),
            )
        result = await self.session.execute(stmt)

        deleted_count = getattr(result, "rowcount", None)
        if deleted_count is not None and deleted_count != len(ids):
            logger.warning(
                "template_elements.delete.partial",
                template_id=str(template_id),
                requested_count=len(ids),
                deleted_count=deleted_count,
            )

    async def get_all_by_template(self, template_id: uuid.UUID) -> Sequence[TemplateElement]:
        statement = (
            select(TemplateElement)
            .where(TemplateElement.template_id == template_id)
            .order_by(TemplateElement.order)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()