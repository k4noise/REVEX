from __future__ import annotations

import uuid
from typing import Optional, Sequence

from fastapi_hypermodel import HALLinks, FrozenDict, HALFor, HALHyperModel
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from core.auth.user_model import User
from template.models.template import Template
from template.schemas.template_element import TemplatePatchRequest, TemplateElementResponse


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


class TemplateStructure(CamelCaseModel):
    id: uuid.UUID
    name: str
    max_score: int
    is_draft: Optional[bool] = None
    elements: Sequence[TemplateElementResponse]

    @staticmethod
    def from_domain(template: Template, tree: list[TemplateElementResponse]) -> "TemplateStructure":
        return TemplateStructure(
            id=template.id,
            name=template.name,
            max_score=template.max_score,
            is_draft=template.is_draft,
            elements=tree,
        )


class TemplateCreationResponse(HALHyperModel):
    id: uuid.UUID

    links: HALLinks = FrozenDict({
        "self": HALFor("parse_template"),
        "get_template": HALFor("get_template", {"template_id": "<id>"}),
    })


class TemplateDetailResponse(TemplateStructure, HALHyperModel):
    user: User = Field(exclude=True)

    links: HALLinks = FrozenDict({
        "self": HALFor("get_template", {"template_id": "<id>"}),
        "update": HALFor(
            "save_modified_template",
            {"template_id": "<id>"},
            condition=lambda values: values["user"] and values["user"].is_teacher(),
        ),
        "publish": HALFor(
            "publish_template",
            {"template_id": "<id>"},
            condition=lambda values: values["user"] and values["user"].is_teacher() and values.get("is_draft"),
        ),
        "delete": HALFor(
            "remove_template",
            {"template_id": "<id>"},
            condition=lambda values: values["user"] and values["user"].is_teacher(),
        ),
        "all": HALFor("get_templates"),
    })

    @staticmethod
    def from_domain(template: Template, user: User, tree: list[TemplateElementResponse]) -> "TemplateDetailResponse":
        return TemplateDetailResponse(
            id=template.id,
            name=template.name,
            max_score=template.max_score,
            is_draft=template.is_draft,
            user=user,
            elements=tree,
        )


class TemplateCourseSummary(HALHyperModel):
    id: uuid.UUID
    name: str
    is_draft: bool

    user: User = Field(exclude=True)

    links: HALLinks = FrozenDict({
        "self": HALFor("get_template", {"template_id": "<id>"}),
        "get_template": HALFor(
            "get_template",
            {"template_id": "<id>"},
            condition=lambda values: values["user"] and values["user"].is_teacher(),
        ),
        "get_reports": HALFor(
            "get_reports_by_template",
            {"template_id": "<id>"},
            condition=lambda values: values["user"] and values["user"].is_instructor(),
        ),
        "create_report": HALFor(
            "create_report",
            {"template_id": "<id>"},
            condition=lambda values: values["user"] and values["user"].is_student(),
        ),
    })

    model_config = ConfigDict(
        serialize_by_alias=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

    @staticmethod
    def from_domain(template: Template, user: User) -> "TemplateCourseSummary":
        return TemplateCourseSummary(
            id=template.id,
            name=template.name,
            is_draft=template.is_draft,
            user=user,
        )


class TemplateCourseCollection(HALHyperModel):
    course_name: str
    templates: Sequence[TemplateCourseSummary] = Field(default_factory=list)

    user: User = Field(exclude=True)

    links: HALLinks = FrozenDict({
        "self": HALFor("get_templates"),
        "add_template": HALFor(
            "parse_template",
            condition=lambda values: values["user"] and values["user"].is_teacher(),
        ),
    })

    model_config = ConfigDict(
        serialize_by_alias=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

    @staticmethod
    def from_domain(
            templates: Sequence[Template], user: User, course_name: str
    ) -> "TemplateCourseCollection":
        return TemplateCourseCollection(
            course_name=course_name,
            user=user,
            templates=[TemplateCourseSummary.from_domain(t, user) for t in templates],
        )