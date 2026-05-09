from __future__ import annotations

import uuid
from enum import Enum
from typing import Literal, Optional, Union, Sequence

from fastapi_hypermodel import HyperModel, UrlFor
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel


class DisplayMode(str, Enum):
    ALWAYS = "always"
    PREFER = "prefer"


class ElementType(str, Enum):
    TEXT = "text"
    HEADER = "header"
    IMAGE = "image"
    TABLE = "table"
    ROW = "row"
    CELL = "cell"
    QUESTION = "question"
    ANSWER = "answer"
    CONTAINER = "container"


class BaseElementPayload(BaseModel):
    id: uuid.UUID
    parent_element_id: Optional[uuid.UUID] = None
    order: int
    display_mode: Optional[DisplayMode]
    marker: Optional[str] = None

    model_config = ConfigDict(
        serialize_by_alias=True,
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class TextElementPayload(BaseElementPayload):
    type: Literal[ElementType.TEXT]
    data: str


class HeaderElementPayload(BaseElementPayload):
    type: Literal[ElementType.HEADER]
    data: str
    level: int = Field(ge=1, le=6)


class ImageElementPayload(BaseElementPayload):
    type: Literal[ElementType.IMAGE]
    media_key: str
    alt_text: Optional[str] = None


class QuestionElementPayload(BaseElementPayload):
    type: Literal[ElementType.QUESTION]
    data: str
    max_score: float = Field(gt=0)


class AnswerElementPayload(BaseElementPayload):
    type: Literal[ElementType.ANSWER]
    data: str


class ContainerElementPayload(BaseElementPayload):
    type: Literal[ElementType.CONTAINER]


class TableElementPayload(BaseElementPayload):
    type: Literal[ElementType.TABLE]


class RowElementPayload(BaseElementPayload):
    type: Literal[ElementType.ROW]


class CellElementPayload(BaseElementPayload):
    type: Literal[ElementType.CELL]
    rowspan: Optional[int] = None
    colspan: Optional[int] = None


AnyElementPayload = Union[
    TextElementPayload,
    HeaderElementPayload,
    ImageElementPayload,
    QuestionElementPayload,
    AnswerElementPayload,
    ContainerElementPayload,
    TableElementPayload,
    RowElementPayload,
    CellElementPayload,
]


class ElementUpdatePayload(BaseModel):
    id: uuid.UUID
    parent_element_id: Optional[uuid.UUID] = Field(None, alias="parentElementId")
    order: Optional[int] = None
    data: Optional[str] = None
    level: Optional[int] = Field(None, ge=1, le=6)
    media_key: Optional[str] = None
    alt_text: Optional[str] = None
    max_score: Optional[float] = Field(None, gt=0)
    rowspan: Optional[int] = None
    colspan: Optional[int] = None
    display_mode: Optional[DisplayMode] = None
    marker: Optional[str] = None
    similar_theory: Optional[list[str]] = None
    question_id: Optional[str] = None
    question_text: Optional[str] = None

    model_config = ConfigDict(
        serialize_by_alias=True,
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class ElementDeletePayload(BaseModel):
    id: uuid.UUID


class PatchAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class BasePatch(BaseModel):
    action: PatchAction


class CreateElementPatch(BasePatch):
    action: Literal[PatchAction.CREATE]
    payload: AnyElementPayload


class UpdateElementPatch(BasePatch):
    action: Literal[PatchAction.UPDATE]
    payload: ElementUpdatePayload


class DeleteElementPatch(BasePatch):
    action: Literal[PatchAction.DELETE]
    payload: ElementDeletePayload


AnyPatch = Union[CreateElementPatch, UpdateElementPatch, DeleteElementPatch]


class TemplatePatchRequest(BaseModel):
    patches: list[AnyPatch]


class TemplateElementResponse(HyperModel):
    id: uuid.UUID
    type: ElementType
    order: int
    parent_element_id: Optional[uuid.UUID] = Field(None, alias="parentElementId")
    display_mode: Optional[DisplayMode] = Field(None, alias="displayMode")
    data: Optional[str] = None

    level: Optional[int] = None
    media_key: Optional[str] = Field(default=None, exclude=True)
    alt_text: Optional[str] = None
    max_score: Optional[float] = None
    hint: Optional[str] = None
    marker: Optional[str] = None
    rowspan: Optional[int] = None
    colspan: Optional[int] = None
    children: list["TemplateElementResponse"] = Field(default_factory=list)

    image_url: Optional[UrlFor] = UrlFor(
        "get_image",
        {"file_key": "<media_key>"},
        condition=lambda values: bool(values.get("media_key")),
    )

    model_config = ConfigDict(
        serialize_by_alias=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

    @classmethod
    def from_db(cls, value) -> "TemplateElementResponse":
        if isinstance(value, cls):
            return value.model_copy(deep=True)

        if isinstance(value, dict):
            payload = dict(value)
            payload.setdefault("children", [])
            return cls.model_validate(payload)

        properties = getattr(value, "properties", None) or {}

        payload = {
            "id": getattr(value, "id"),
            "type": getattr(value, "type"),
            "order": getattr(value, "order"),
            "parent_element_id": getattr(value, "parent_element_id", None),
            "display_mode": getattr(value, "display_mode", None),
            "data": getattr(value, "data", None),
            "marker": getattr(value, "marker", None) or properties.get("marker"),
            "level": properties.get("level"),
            "media_key": properties.get("media_key"),
            "alt_text": properties.get("alt_text"),
            "max_score": properties.get("max_score"),
            "hint": properties.get("hint"),
            "rowspan": properties.get("rowspan"),
            "colspan": properties.get("colspan"),
            "children": [],
        }

        return cls.model_validate(payload)


def build_template_tree(elements: Sequence) -> list[TemplateElementResponse]:
    dto_items = [TemplateElementResponse.from_db(element) for element in elements]

    by_id: dict[uuid.UUID, TemplateElementResponse] = {
        item.id: item for item in dto_items
    }

    roots: list[TemplateElementResponse] = []

    for item in dto_items:
        if item.parent_element_id and item.parent_element_id in by_id:
            by_id[item.parent_element_id].children.append(item)
        else:
            roots.append(item)

    def sort_recursive(nodes: list[TemplateElementResponse]) -> None:
        nodes.sort(key=lambda x: x.order)
        for node in nodes:
            sort_recursive(node.children)

    sort_recursive(roots)
    return roots


def build_template_tree_for_report(elements: Sequence) -> list[TemplateElementResponse]:
    full_tree = build_template_tree(elements)

    def transform(nodes: list[TemplateElementResponse]) -> list[TemplateElementResponse]:
        result: list[TemplateElementResponse] = []
        for node in nodes:
            if node.type == ElementType.ANSWER:
                node.data = None
            node.children = transform(node.children)
            result.append(node)
        return result

    return transform(full_tree)


TemplateElementResponse.model_rebuild()