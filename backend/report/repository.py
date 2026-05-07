import uuid
from typing import Sequence

from sqlalchemy import Select, select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from report.model import Report
from report.schemas.report_status import ReportStatus
from template.models.template import Template


class ReportRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, report: Report) -> None:
        self.session.add(report)
        await self.session.flush()

    async def get(self, report_id: uuid.UUID) -> Report | None:
        statement: Select = select(Report).where(Report.id == report_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_with_template_and_answers(
            self,
            report_id: uuid.UUID,
    ) -> Report | None:
        statement: Select = (
            select(Report)
            .where(Report.id == report_id)
            .options(
                selectinload(Report.template).selectinload(Template.elements),
                selectinload(Report.answers),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_last_by_author(
            self,
            author_id: str,
            template_id: uuid.UUID,
    ) -> Report | None:
        statement: Select = (
            select(Report)
            .where(
                Report.template_id == template_id,
                Report.author_id == author_id,
                )
            .order_by(desc(Report.created_at))
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_all_by_template(self, template_id: uuid.UUID) -> Sequence[Report]:
        statement: Select = (
            select(Report)
            .where(Report.template_id == template_id)
            .order_by(desc(Report.created_at))
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_all_by_author_and_status(
            self,
            template_id: uuid.UUID,
            author_id: str,
            status: ReportStatus,
    ) -> Sequence[Report]:
        statement: Select = (
            select(Report)
            .where(
                Report.template_id == template_id,
                Report.author_id == author_id,
                Report.status == status,
                )
            .order_by(desc(Report.created_at))
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def update(self, report: Report) -> None:
        self.session.add(report)

    async def delete(self, report: Report) -> None:
        await self.session.delete(report)