import uuid
from typing import Any, Sequence

from sqlalchemy import insert, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from template.models.template_element import TemplateElement


class TemplateElementRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_create_raw(self, payloads: list[dict[str, Any]]):
        if not payloads:
            return

        await self.session.execute(
            insert(TemplateElement),
            payloads
        )

    async def bulk_update_from_map(self, template_id: uuid.UUID, updates_map: dict[uuid.UUID, dict[str, Any]]):
        if not updates_map:
            return

        stmt = select(TemplateElement).where(TemplateElement.id.in_(list(updates_map.keys())))
        result = await self.session.execute(stmt)
        elements = result.scalars().all()

        for el in elements:
            data = updates_map[el.id]

            if 'properties' in data:
                el.properties = (el.properties or {}) | data.pop('properties')

            for key, value in data.items():
                if hasattr(el, key):
                    setattr(el, key, value)

        await self.session.flush()

    async def bulk_delete(self, template_id: uuid.UUID, ids: list[uuid.UUID]):
        if not ids:
            return
        await self.session.execute(
            delete(TemplateElement).where(
                TemplateElement.template_id == template_id,
                TemplateElement.id.in_(ids)
            )
        )

    async def get_all_by_template(self, template_id: uuid.UUID) -> Sequence[TemplateElement]:
        statement = (
                select(TemplateElement)
                .where(TemplateElement.template_id == template_id)
                .order_by(TemplateElement.order)
            )
        result = await self.session.execute(statement)
        return result.scalars().all()