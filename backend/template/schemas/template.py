from __future__ import annotations

import uuid
from typing import Optional, Sequence

from fastapi_hypermodel import HALLinks, FrozenDict, HALFor
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from answer.schemas import AnswerResponse, PreGradedAnswerResponse
from core.auth.user_model import User
from core.halhypermodel import HALHyperModel
from lti.services.nrps import NrpsService
from report.model import Report
from report.schemas.report import MinimalReportResponse
from report.schemas.report_status import ReportStatus
from template.models.template import Template
from template.schemas.template_element import (
    TemplatePatchRequest,
    TemplateElementResponse,
    build_template_tree_for_report,
)


class CamelCaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias=True,
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class TemplateUpdateRequest(CamelCaseModel):
    name: Optional[str] = None
    max_score: Optional[int] = None
    elements: Optional[TemplatePatchRequest] = None


class TemplateManyRequest(CamelCaseModel):
    ids: list[uuid.UUID]


class TemplateStructure(CamelCaseModel):
    id: uuid.UUID
    name: str
    max_score: int
    is_draft: Optional[bool] = None
    elements: Sequence[TemplateElementResponse]

    @staticmethod
    def from_domain(
            template: Template,
            tree: list[TemplateElementResponse],
    ) -> "TemplateStructure":
        return TemplateStructure(
            id=template.id,
            name=template.name,
            max_score=template.max_score,
            is_draft=template.is_draft,
            elements=tree,
        )


class TemplateCreationResponse(HALHyperModel):
    id: uuid.UUID

    links: HALLinks = FrozenDict(
        {
            "self": HALFor("parse_template"),
            "get_template": HALFor("get_template", {"template_id": "<id>"}),
        }
    )


class TemplateDetailResponse(TemplateStructure, HALHyperModel):
    user: User = Field(exclude=True)
    can_create_report: bool = Field(default=False, exclude=True)

    links: HALLinks = FrozenDict(
        {
            "self": HALFor("get_template", {"template_id": "<id>"}),
            "update": HALFor(
                "save_modified_template",
                {"template_id": "<id>"},
                condition=lambda v: v["user"] and v["user"].is_teacher(),
            ),
            "publish": HALFor(
                "publish_template",
                {"template_id": "<id>"},
                condition=lambda v: v["user"] and v["user"].is_teacher() and v.get("is_draft"),
            ),
            "delete": HALFor(
                "remove_template",
                {"template_id": "<id>"},
                condition=lambda v: v["user"] and v["user"].is_teacher(),
            ),
            "upload_image": HALFor(
                "save_image",
                condition=lambda v: v["user"] and v["user"].is_teacher(),
            ),
            "get_reports": HALFor(
                "get_reports_by_template",
                {"template_id": "<id>"},
            ),
            "create_report": HALFor(
                "create_report",
                {"template_id": "<id>"},
                condition=lambda v: v["user"]
                                    and not v["user"].is_teacher()
                                    and v.get("can_create_report", False),
            ),
            "all": HALFor("get_templates"),
        }
    )

    @staticmethod
    def from_domain(template, user, tree, can_create_report: bool = False):
        return TemplateDetailResponse(
            id=template.id,
            name=template.name,
            max_score=template.max_score,
            is_draft=template.is_draft,
            user=user,
            elements=tree,
            can_create_report=can_create_report,
        )

class TemplateCourseSummary(HALHyperModel):
    id: uuid.UUID
    name: str
    is_draft: bool

    reports: Sequence[MinimalReportResponse] = Field(default_factory=list)

    user: User = Field(exclude=True)
    can_create_report: bool = Field(exclude=True)

    links: HALLinks = FrozenDict(
        {
            "self": HALFor("get_template", {"template_id": "<id>"}),
            "get_template": HALFor(
                "get_template",
                {"template_id": "<id>"},
                condition=lambda values: values["user"]
                                         and values["user"].is_teacher(),
            ),
            "delete": HALFor(
                "remove_template",
                {"template_id": "<id>"},
                condition=lambda values: values.get("user")
                                         and values["user"].is_teacher(),
            ),
            "publish": HALFor(
                "publish_template",
                {"template_id": "<id>"},
                condition=lambda values: values["is_draft"] is True,
            ),
            "get_reports": HALFor(
                "get_reports_by_template",
                {"template_id": "<id>"},
                condition=lambda values: values["user"]
                                         and values["user"].is_instructor(),
            ),
            "create_report": HALFor(
                "create_report",
                {"template_id": "<id>"},
                condition=lambda values: values["user"]
                                         and not values["user"].is_teacher()
                                         and values.get("can_create_report", False),
            ),
        }
    )

    model_config = ConfigDict(
        serialize_by_alias=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

    @staticmethod
    def from_domain(template: Template, user: User) -> "TemplateCourseSummary":
        loaded_reports = []
        can_create = True

        if "reports" in template.__dict__:
            sorted_reports = sorted(
                template.reports, key=lambda r: r.created_at, reverse=True
            )
            loaded_reports = [
                MinimalReportResponse.from_domain(r, user) for r in sorted_reports
            ]

            if loaded_reports:
                last_report = loaded_reports[0]
                can_create = last_report.status == ReportStatus.GRADED

        return TemplateCourseSummary(
            id=template.id,
            name=template.name,
            is_draft=template.is_draft,
            reports=loaded_reports,
            user=user,
            can_create_report=can_create,
        )


class TemplateCourseCollection(HALHyperModel):
    course_name: str
    templates: Sequence[TemplateCourseSummary] = Field(default_factory=list)

    user: User = Field(exclude=True)

    links: HALLinks = FrozenDict(
        {
            "self": HALFor("get_templates"),
            "add_template": HALFor(
                "parse_template",
                condition=lambda values: values["user"]
                                         and values["user"].is_teacher(),
            ),
            "publish_many": HALFor(
                "publish_many_templates",
                condition=lambda values: values["user"]
                                         and values["user"].is_teacher(),
            ),
            "delete_many": HALFor(
                "delete_many_templates",
                condition=lambda values: values["user"]
                                         and values["user"].is_teacher(),
            ),
        }
    )

    model_config = ConfigDict(
        serialize_by_alias=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

    @staticmethod
    def from_domain(
            templates: Sequence[Template],
            user: User,
            course_name: str,
    ) -> "TemplateCourseCollection":
        return TemplateCourseCollection(
            course_name=course_name,
            user=user,
            templates=[TemplateCourseSummary.from_domain(t, user) for t in templates],
        )


class FullWorkResponse(HALHyperModel):
    template: "TemplateStructure"
    id: uuid.UUID
    status: ReportStatus
    grader_name: Optional[str] = None
    score: Optional[float] = None
    answers: Sequence[AnswerResponse | PreGradedAnswerResponse]

    author_id: str = Field(exclude=True)
    user: User = Field(exclude=True)

    links: HALLinks = FrozenDict(
        {
            "self": HALFor("get_report", {"report_id": "<id>"}),
            "save": HALFor(
                "update_answers",
                {"report_id": "<id>"},
                condition=lambda values: values["user"]
                                         and values["user"].is_student(),
            ),
            "submit": HALFor(
                "send_to_grade",
                {"report_id": "<id>"},
                condition=lambda values: values["user"]
                                         and values["user"].is_student(),
            ),
            "unsubmit": HALFor(
                "cancel_send_to_grade",
                {"report_id": "<id>"},
                condition=lambda values: values["user"]
                                         and values["user"].is_student(),
            ),
            "grade": HALFor(
                "save_grades",
                {"report_id": "<id>"},
                condition=lambda values: values["user"]
                                         and values["user"].is_instructor()
                                         and values["user"].id != values["author_id"],
            ),
            "get_hint": HALFor(
                "get_hint",
                {"report_id": "<id>"},
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
    def from_domain(
            report: Report,
            user: User,
            nrps: NrpsService | None,
    ) -> "FullWorkResponse":
        elements_by_id_map = {element.id: element for element in report.template.elements}

        template_tree = build_template_tree_for_report(report.template.elements)

        dto_factory = (
            PreGradedAnswerResponse.from_domain
            if user.is_instructor() and user.id != report.author_id
            else AnswerResponse.from_domain
        )

        grader_name: Optional[str] = None
        if nrps is not None and report.grader_id is not None:
            grader = nrps.get_user_by_id(report.grader_id)
            grader_name = grader.name if grader is not None else None

        return FullWorkResponse(
            template=TemplateStructure.from_domain(report.template, template_tree),
            id=report.id,
            status=report.status,
            grader_name=grader_name,
            score=report.score,
            answers=[dto_factory(answer, elements_by_id_map) for answer in report.answers],
            user=user,
            author_id=report.author_id,
        )