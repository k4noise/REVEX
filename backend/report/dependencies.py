from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from answer.repository import AnswerRepository
from answer.services.answer import AnswerService
from answer.utils.embedder import TextEmbedder
from core.db import get_session
from report.repository import ReportRepository
from report.services.hint_context import HintContextService
from report.services.report import ReportService


_embedder = TextEmbedder()
_hint_context_service = HintContextService(_embedder)


def get_hint_context_service() -> HintContextService:
    return _hint_context_service

def get_report_service(session: AsyncSession = Depends(get_session)) -> ReportService:
    return ReportService(ReportRepository(session), AnswerService(AnswerRepository(session)))