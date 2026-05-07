from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_session
from core.dependencies import get_background_task_service
from core.background_service import BackgroundTaskService
from lti.dependencies import get_nrps_service
from lti.services.nrps import NrpsService

from answer.repository import AnswerRepository
from answer.services.answer import AnswerService
from answer.services.grade import GradeService
from report.repository import ReportRepository
from report.services.report import ReportService


def get_answer_service(
        session: AsyncSession = Depends(get_session),
) -> AnswerService:
    return AnswerService(AnswerRepository(session))


def get_report_service(
        session: AsyncSession = Depends(get_session),
) -> ReportService:
    return ReportService(
        ReportRepository(session),
        AnswerService(AnswerRepository(session)),
    )


def get_grade_service(
        report_service: ReportService = Depends(get_report_service),
        background_service: BackgroundTaskService = Depends(get_background_task_service),
        nrps_service: NrpsService = Depends(get_nrps_service),
) -> GradeService:
    return GradeService(report_service, background_service, nrps_service)