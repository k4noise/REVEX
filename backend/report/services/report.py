from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

import structlog
from pylti1p3.message_launch import MessageLaunch

from answer.schemas import NewAnswerData, UpdateAnswerDataRequest
from answer.services.answer import AnswerService
from core.auth.user_model import User
from lti.services.launch import LaunchService
from lti.services.nrps import NrpsService
from report.exceptions import (
    NotOwnerAccessDeniedException,
    ReportStateAccessDeniedException,
    ReportNotFoundException,
)
from report.model import Report
from report.schemas.report_status import ReportStatus
from report.services.report_access_verifier import ReportAccessVerifier, UpdateGradeInfo
from report.repository import ReportRepository
from report.schemas.report import (
    ReportCreationResponse,
    AllReportsResponse,
    AllReportsByUserResponse,
)
from template.exceptions import InvalidActionException
from template.schemas.template import TemplateDetailResponse, FullWorkResponse


def _flatten_elements(elements: Sequence) -> list:
    result: list = []

    def _walk(nodes: Sequence) -> None:
        for node in nodes:
            result.append(node)
            children = getattr(node, "children", None) or []
            if children:
                _walk(children)

    _walk(elements)
    return result


class ReportService:
    def __init__(
            self,
            repository: ReportRepository,
            answer_service: AnswerService,
            logger=structlog.get_logger(__name__),
    ):
        self.repository = repository
        self.answer_service = answer_service
        self.logger = logger

    async def create(
            self,
            user: User,
            template: TemplateDetailResponse,
    ) -> ReportCreationResponse:
        self.logger.info(
            "report.create.start",
            template_id=str(template.id),
            user_id=user.id,
        )

        current_report = await self.repository.get_last_by_author(
            user.id,
            template.id,
        )

        if current_report and current_report.status is not ReportStatus.GRADED:
            self.logger.warning(
                "report.create.already_exists",
                last_report_id=str(current_report.id),
                last_status=current_report.status.value,
            )
            raise InvalidActionException("отчет уже существует")

        current_answers = (
            {answer.element_id: answer for answer in current_report.answers}
            if current_report
            else {}
        )

        flat_elements = _flatten_elements(template.elements)
        answer_elements = [
            el for el in flat_elements if getattr(el, "type", None) == "answer"
        ]

        new_report = Report(
            template_id=template.id,
            author_id=user.id,
            status=ReportStatus.CREATED,
        )
        await self.repository.create(new_report)

        await self.answer_service.create(
            new_report.id,
            [
                NewAnswerData.from_domain(
                    element,
                    current_answers.get(element.id),
                )
                for element in answer_elements
            ],
        )

        self.logger.info(
            "report.create.ok",
            report_id=str(new_report.id),
            template_id=str(template.id),
            answers_count=len(answer_elements),
        )

        return ReportCreationResponse(id=new_report.id)

    async def get(
            self,
            user: User,
            report_id: uuid.UUID,
            nrps: NrpsService | None,
    ) -> FullWorkResponse:
        report = await self._get(report_id, user)
        return FullWorkResponse.from_domain(report, user, nrps)

    async def get_all_by_template(
            self,
            template: TemplateDetailResponse,
            user: User,
            launch_service: LaunchService,
            message_launch: MessageLaunch
    ) -> AllReportsResponse:
        all_reports = await self.repository.get_all_by_template(template.id)
        bind_map = await launch_service.get_course_users_bind_map(message_launch, user.course_id)
        self.logger.info(
            "report.list.by_template",
            template_id=str(template.id),
            count=len(all_reports),
        )
        return AllReportsResponse.from_domain(template, all_reports, user, bind_map)

    async def get_all_by_template_and_status(
            self,
            user: User,
            template: TemplateDetailResponse,
            author_id: str,
            status: str,
            launch_service: LaunchService,
            message_launch: MessageLaunch
    ) -> AllReportsByUserResponse:
        if not user.is_instructor() and author_id != user.id:
            raise NotOwnerAccessDeniedException()

        try:
            status_enum = ReportStatus(status.lower())
        except ValueError:
            raise InvalidActionException("неизвестный статус отчёта")

        if status_enum in (ReportStatus.SAVED, ReportStatus.CREATED):
            raise ReportStateAccessDeniedException(status_enum)

        all_reports = await self.repository.get_all_by_author_and_status(
            template.id,
            author_id,
            status_enum,
        )
        bind_map = await launch_service.get_course_users_bind_map(message_launch, user.course_id)

        self.logger.info(
            "report.list.by_template_and_status",
            template_id=str(template.id),
            author_id=author_id,
            status=status_enum.value,
            count=len(all_reports),
        )

        return AllReportsByUserResponse.from_domain(template, all_reports, user, bind_map)

    async def save(
            self,
            user: User,
            report_id: uuid.UUID,
            answers: Sequence[UpdateAnswerDataRequest],
    ) -> None:
        report = await self._get(report_id, user)
        await self._mark(report, ReportStatus.SAVED)
        await self.answer_service.update_data(report_id, answers)
        self.logger.info(
            "report.answers.updated",
            report_id=str(report_id),
        )

    async def submit(self, user: User, report_id: uuid.UUID) -> None:
        report = await self._get(report_id, user)
        await self._mark(report, ReportStatus.SUBMITTED)
        self.logger.info(
            "report.submit",
            report_id=str(report_id),
        )

    async def unsubmit(self, user: User, report_id: uuid.UUID) -> None:
        report = await self._get(report_id, user)
        await self._mark(report, ReportStatus.SAVED)
        self.logger.info(
            "report.unsubmit",
            report_id=str(report_id),
        )

    async def grade(
            self,
            user: User,
            report_id: uuid.UUID,
            report_updates: UpdateGradeInfo,
    ) -> None:
        report = await self._get(report_id, user)
        report.grader_id = report_updates.grader_id
        report.score = report_updates.final_score
        await self._mark(report, ReportStatus.GRADED)
        await self.answer_service.update_scores(
            report_id,
            report_updates.new_scores,
        )
        self.logger.info(
            "report.grade",
            report_id=str(report_id),
            grader_id=report.grader_id,
            final_score=report.score,
        )

    async def _get(self, report_id: uuid.UUID, user: User) -> Report:
        report = await self.repository.get_with_template_and_answers(
            report_id,
        )
        if report is None:
            self.logger.warning(
                "report.get.not_found",
                report_id=str(report_id),
            )
            raise ReportNotFoundException(report_id)

        ReportAccessVerifier(report).is_valid_context(user)
        return report

    async def _mark(self, report: Report, status: ReportStatus) -> Report:
        ReportAccessVerifier(report).is_valid_transition(status)
        report.status = status
        report.updated_at = datetime.now()
        await self.repository.update(report)
        return report