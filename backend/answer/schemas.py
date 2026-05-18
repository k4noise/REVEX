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
    PARAM_PREGRADE_FAILED = "param_pregrade_failed"
    MISSING_NUMBER = "missing_number"
    LITERAL_MISSING = "literal_missing"
    KEYWORD_MISMATCH = "keyword_mismatch"
    PARAM_MISMATCH = "param_mismatch"
    REGEX_NO_MATCH = "regex_no_match"
    SEMANTIC_MISMATCH = "semantic_mismatch"
    WEAK_SEMANTIC_MATCH = "weak_semantic_match"


@dataclass
class ErrorDetail:
    type: ErrorType
    expected: str = ""
    actual: Optional[str] = None


@dataclass
class GradeResult:
    score: float
    errors: List[ErrorDetail]
    needs_manual_review: bool = False
    type: str = "pipeline"
    explanation: Optional[str] = None


@dataclass
class GradingContext:
    raw_given: str
    raw_reference: str

    resolved_reference: str = ""
    remaining_given: str = ""
    remaining_reference: str = ""

    numbers_checked_by_params: set[str] = field(default_factory=set)

    fast_mode: bool = False
    strict_match: bool = False

    errors: List[ErrorDetail] = field(default_factory=list)
    score: Optional[float] = None
    is_perfect_match: bool = False

    def __post_init__(self):
        if not self.remaining_given:
            self.remaining_given = self.raw_given
        if not self.remaining_reference:
            self.remaining_reference = self.raw_reference
        if not self.resolved_reference:
            self.resolved_reference = self.raw_reference

    def add_error(self, error: ErrorDetail) -> None:
        self.errors.append(error)

    def should_stop(self, threshold: float) -> bool:
        if not self.fast_mode:
            return False
        return self.score is not None and self.score >= threshold

    @property
    def final_score(self) -> float:
        if self.is_perfect_match:
            return 1.0
        if self.score is not None:
            return self.score
        return 0.0


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
    comment: Optional[str] = None

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
            comment=answer.comment if answer else None,
        )


class UpdateAnswerDataRequest(CamelCaseModel):
    id: uuid.UUID
    data: Optional[dict] = None


class UpdateAnswerScoresRequest(CamelCaseModel):
    id: uuid.UUID
    score: Optional[float] = 0
    comment: Optional[str] = None


class AnswerResponse(CamelCaseModel):
    id: uuid.UUID
    element_id: uuid.UUID
    score: Optional[float] = None
    data: Optional[dict] = None
    comment: Optional[str] = None

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
            comment=answer_model.comment,
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
            comment=base.comment,
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
            comment=answer.comment,
            weight=getattr(answer, 'weight', None),
            reference=getattr(answer, 'reference', None),
            root_id=getattr(answer, 'root_id', None),
            pre_grade=pre_grade_result,
        )