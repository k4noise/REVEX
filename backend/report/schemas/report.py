from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Sequence

from fastapi_hypermodel import HALLinks, FrozenDict, HALFor
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from core.auth.user_model import User
from core.halhypermodel import HALHyperModel
from lti.schemas import NrpsUser
from report.model import Report
from report.schemas.report_status import ReportStatus

class ReportsData(BaseModel):
    owned: Optional[Sequence[MinimalReportInfoResponse]] = Field(default=None)
    to_grade: Optional[Sequence[MinimalReportInfoResponse]] = Field(default=None)

    model_config = ConfigDict(
        serialize_by_alias=True,
        populate_by_name=True,
        alias_generator=to_camel,
        exclude_none=True
    )

class ReportCreationResponse(HALHyperModel):
    id: uuid.UUID

    links: HALLinks = FrozenDict(
        {
            "self": HALFor("get_report", {"report_id": "<id>"}),
        }
    )


class MinimalReportResponse(HALHyperModel):
    created_at: datetime
    report_id: uuid.UUID
    template_id: uuid.UUID
    status: ReportStatus

    user: User = Field(exclude=True)

    links: HALLinks = FrozenDict(
        {
            "self": HALFor("get_report", {"report_id": "<report_id>"}),
            "create_report": HALFor(
                "create_report",
                {"template_id": "<template_id>"},
                condition=lambda values: values["user"]
                                         and values["user"].is_student(),
            ),
        }
    )

    model_config = ConfigDict(
        serialize_by_alias=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

    @staticmethod
    def from_domain(report: Report, user: User) -> "MinimalReportResponse":
        return MinimalReportResponse(
            created_at=report.created_at,
            report_id=report.id,
            template_id=report.template_id,
            status=report.status,
            user=user,
        )


class MinimalReportInfoResponse(MinimalReportResponse):
    author_name: Optional[str]
    score: Optional[float] = None

    @staticmethod
    def from_domain_with_user(
            report: Report, author: NrpsUser, user: User
    ) -> "MinimalReportInfoResponse":
        base = MinimalReportResponse.from_domain(report, user)
        return MinimalReportInfoResponse(
            created_at=base.created_at,
            report_id=base.report_id,
            template_id=base.template_id,
            status=base.status,
            user=user,
            links=base.links,
            author_name=author.name if author else None,
            score=report.score,
        )


class AllReportsByUserResponse(BaseModel):
    template_name: str
    template_id: uuid.UUID
    max_score: float
    reports: Sequence[MinimalReportInfoResponse]

    @staticmethod
    def from_domain(
            template: "TemplateDetailResponse",
            reports: Sequence[Report],
            user: User,
            bind_map: dict[str, NrpsUser]
    ) -> "AllReportsByUserResponse":
        return AllReportsByUserResponse(
            template_name=template.name,
            template_id=template.id,
            max_score=template.max_score,
            reports=[
                MinimalReportInfoResponse.from_domain_with_user(
                    report,
                    bind_map[report.author_id],
                    user,
                )
                for report in reports
            ],
        )


class AllReportsResponse(HALHyperModel):
    template_name: str
    template_id: uuid.UUID
    max_score: float
    reports: Optional[ReportsData] = Field(default=None)
    user: User = Field(exclude=True)

    links: HALLinks = FrozenDict(
        {
            "self": HALFor("get_reports_by_template", {"template_id": "<template_id>"}),
        }
    )

    model_config = ConfigDict(
        serialize_by_alias=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

    @staticmethod
    def from_domain(
            template: "TemplateDetailResponse",
            all_reports: Sequence[Report],
            user: User,
            bind_map: dict[str, NrpsUser]
    ) -> "AllReportsResponse":
        self_reports = (
            [
                MinimalReportInfoResponse.from_domain_with_user(
                    report, bind_map.get(str(report.author_id)), user
                )
                for report in all_reports
                if report.author_id == str(user.id)
            ]
            if not user.is_teacher()
            else None
        )

        other_reports = (
            [
                MinimalReportInfoResponse.from_domain_with_user(
                    report, bind_map.get(report.author_id), user
                )
                for report in all_reports
                if report.author_id != str(user.id) and (report.status == ReportStatus.SUBMITTED or report.status == ReportStatus.GRADED)
            ]
            if user.is_instructor()
            else None
        )

        reports_data = None
        if self_reports is not None or other_reports is not None:
            reports_data = ReportsData(
                owned=self_reports,
                to_grade=other_reports
            )

        return AllReportsResponse(
            template_name=template.name,
            template_id=template.id,
            max_score=template.max_score,
            user=user,
            reports=reports_data,
        )