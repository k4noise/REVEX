import uuid
from typing import Optional, Sequence

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from template.models.template import Template


class TemplateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, template: Template) -> Template:
        self.session.add(template)
        await self.session.flush()
        return template

    async def get(self, course_id: str, template_id: uuid.UUID) -> Optional[Template]:
        statement = (
            select(Template)
            .options(selectinload(Template.elements))
            .where(
                Template.id == template_id,
                Template.course_id == course_id,
                )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def update(self, template: Template) -> None:
        self.session.add(template)
        await self.session.flush()

    async def delete(self, template: Template) -> None:
        await self.session.delete(template)

    async def get_all_by_course(
            self,
            course_id: str,
            include_drafts: bool = True
    ) -> Sequence[Template]:
        statement = select(Template).where(Template.course_id == course_id)
        if not include_drafts:
            statement = statement.where(Template.is_draft.is_(False))

        statement = statement.order_by(Template.is_draft.asc(), desc(Template.created_at))
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_many(self, course_id: str, template_ids: Sequence[uuid.UUID]) -> Sequence[Template]:
        statement = select(Template).where(
            Template.course_id == course_id,
            Template.id.in_(template_ids)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def delete_many(self, course_id: str, templates: Sequence[Template]) -> None:
        for template in templates:
            if template.course_id == course_id:
                await self.session.delete(template)