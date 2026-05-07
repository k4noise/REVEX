import uuid
from typing import Sequence

from pydantic import BaseModel, Field, ConfigDict

from answer.schemas import UpdateAnswerScoresRequest
from core.auth.user_model import User
from report.exceptions import (
    InvalidCourseAccessDeniedException,
    NotOwnerAccessDeniedException,
    ReportStateAccessDeniedException,
)
from report.model import Report
from report.schemas.report_status import ReportStatus
from template.exceptions import InvalidTransitionException


class ReportAccessVerifier:
    def __init__(self, report: Report):
        self.report = report

    def is_valid_context(self, user: User) -> "ReportAccessVerifier":
        if self.report.template.course_id != user.course_id:
            raise InvalidCourseAccessDeniedException()

        if not user.is_instructor() and self.report.author_id != user.id:
            raise NotOwnerAccessDeniedException()

        if user.is_instructor() and self.report.status in (
                ReportStatus.SAVED,
                ReportStatus.CREATED,
        ):
            raise ReportStateAccessDeniedException(self.report.status)

        return self

    def is_valid_transition(self, new_status: ReportStatus) -> "ReportAccessVerifier":
        allowed = {
            ReportStatus.CREATED: [ReportStatus.SAVED, ReportStatus.SUBMITTED],
            ReportStatus.SAVED: [ReportStatus.SAVED, ReportStatus.SUBMITTED],
            ReportStatus.SUBMITTED: [ReportStatus.SAVED, ReportStatus.GRADED],
            ReportStatus.GRADED: [ReportStatus.GRADED],
        }

        if new_status not in allowed.get(self.report.status, []):
            raise InvalidTransitionException()

        return self


class UpdateGradeInfo(BaseModel):
    id: uuid.UUID
    grader_id: str
    new_scores: Sequence[UpdateAnswerScoresRequest]
    final_score: float = Field(exclude=True)

    model_config = ConfigDict(arbitrary_types_allowed=True)