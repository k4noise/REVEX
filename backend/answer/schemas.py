import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict

from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel
from pydantic import ConfigDict

from answer.model import Answer
from template.models.template_element import TemplateElement
from template.schemas.template_element import TemplateElementResponse


class ErrorType(str, Enum):
    MISSING_NUMBER = "missing_number"
    PARAM_MISMATCH = "param_mismatch"
    PARAM_PREGRADE_FAILED = "param_pregrade_failed"
    LITERAL_MISSING = "literal_missing"
    REGEX_NO_MATCH = "regex_no_match"
    SEMANTIC_MISMATCH = "semantic_mismatch"
    WEAK_SEMANTIC_MATCH = "weak_semantic_match"
    KEYWORD_MISMATCH = "keyword_mismatch"


@dataclass
class ErrorDetail:
    type: ErrorType
    expected: str
    actual: Optional[str] = None


@dataclass
class GradeResult:
    score: float
    errors: List[ErrorDetail]
    needs_manual_review: bool = False
    type: str = "pipeline"


@dataclass
class GradingContext:
    original_given: str
    original_reference: str
    resolved_reference: str
    current_given: str
    current_reference: str
    fast_mode: bool
    strict_match: bool = False
    final_score: float = 1.0
    is_perfect_match: bool = False
    errors: List[ErrorDetail] = field(default_factory=list)

    @property
    def should_stop(self) -> bool:
        if not self.fast_mode:
            return False
        return any(e.type != ErrorType.PARAM_PREGRADE_FAILED for e in self.errors)

    def add_error(self, error: ErrorDetail) -> None:
        self.errors.append(error)


class CamelCaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        from_attributes=True,
    )


class NewAnswerData(CamelCaseModel):
    element_id: uuid.UUID
    score: Optional[float] = None
    data: Optional[dict] = None
    pre_grade: Optional[dict] = None

    @staticmethod
    def from_domain(
            element: TemplateElementResponse,
            answer: Optional[Answer] = None,
    ) -> "NewAnswerData":
        return NewAnswerData(
            element_id=element.id,
            score=answer.score if answer else None,
            data=answer.data if answer else None,
            pre_grade=answer.pre_grade if answer else None,
        )


class UpdateAnswerDataRequest(CamelCaseModel):
    id: uuid.UUID
    data: Optional[dict] = None


class UpdateAnswerScoresRequest(CamelCaseModel):
    id: uuid.UUID
    score: Optional[float] = 0


class AnswerResponse(CamelCaseModel):
    id: uuid.UUID
    element_id: uuid.UUID
    score: Optional[float] = None
    data: Optional[dict] = None

    weight: Optional[float] = Field(default=None, exclude=True)
    reference: Optional[str] = Field(default=None, exclude=True)
    root_id: Optional[uuid.UUID] = Field(default=None, exclude=True)

    @staticmethod
    def find_root(
            element_id: uuid.UUID,
            elements_map: Dict[uuid.UUID, Optional[TemplateElement]],
    ) -> uuid.UUID:
        current_id = element_id
        visited = set()

        while current_id in elements_map:
            if current_id in visited:
                break

            visited.add(current_id)
            current = elements_map[current_id]

            if not current or not getattr(current, "parent_element_id", None):
                break

            current_id = current.parent_element_id

        return current_id

    @staticmethod
    def from_domain(
            answer_model: Answer,
            elements_by_id_map: Dict[uuid.UUID, Optional[TemplateElement]],
    ) -> "AnswerResponse":
        element = elements_by_id_map.get(answer_model.element_id)
        properties = getattr(element, "properties", None) or {}
        return AnswerResponse(
            id=answer_model.id,
            element_id=answer_model.element_id,
            score=answer_model.score,
            data=answer_model.data,
            weight=properties.get("weight"),
            reference=element.data if element is not None else None,
            root_id=AnswerResponse.find_root(
                answer_model.element_id, elements_by_id_map
            ),
        )


class PreGradedAnswerResponse(AnswerResponse):
    pre_grade: Optional[dict] = None

    @staticmethod
    def from_domain(
            answer_model: Answer,
            elements_by_id_map: Dict[uuid.UUID, Optional[TemplateElement]],
    ) -> "PreGradedAnswerResponse":
        base = AnswerResponse.from_domain(answer_model, elements_by_id_map)
        return PreGradedAnswerResponse(
            id=base.id,
            element_id=base.element_id,
            score=base.score,
            data=base.data,
            weight=base.weight,
            reference=base.reference,
            root_id=base.root_id,
            pre_grade=answer_model.pre_grade,
        )

    @staticmethod
    def from_response(answer: AnswerResponse, pre_grade_result: dict):
        return PreGradedAnswerResponse(
            id=answer.id,
            element_id=answer.element_id,
            score=answer.score,
            data=answer.data,
            pre_grade=pre_grade_result,
        )