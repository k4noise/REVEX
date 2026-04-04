from __future__ import annotations

import uuid
from enum import Enum
from typing import Literal, Optional, Union, Any

from fastapi_hypermodel import HALLinks, FrozenDict, HALFor, HyperModel, UrlFor
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel

from core.halhypermodel import HALHyperModel


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
    TextElementPayload, HeaderElementPayload, ImageElementPayload, QuestionElementPayload,
    AnswerElementPayload, ContainerElementPayload, TableElementPayload, RowElementPayload, CellElementPayload
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
    children: list[TemplateElementResponse] = Field(default_factory=list)

    image_url: Optional[UrlFor] = UrlFor(
        "get_image",
        {"file_key": "<media_key>"},
        condition=lambda values: bool(values.get("media_key"))
    )

    model_config = ConfigDict(
        serialize_by_alias=True,
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


    @classmethod
    def from_db(cls, db_element) -> "TemplateElementResponse":
        properties = db_element.properties or {}
        base_data = {
            "id": db_element.id,
            "type": db_element.type,
            "order": db_element.order,
            "parent_element_id": db_element.parent_element_id,
            "display_mode": db_element.display_mode,
            "data": db_element.data,
            "marker": db_element.marker if hasattr(db_element, 'marker') else properties.get("marker"),
        }
        properties = db_element.properties or {}
        return cls.model_validate({**base_data, **properties})