from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_session
from template.repository.template import TemplateRepository
from template.repository.template_element import TemplateElementRepository
from template.service.parser import DedocTemplateParser
from template.service.template import TemplateService
from template.service.template_element import TemplateElementService


def get_template_service(session: AsyncSession = Depends(get_session)) -> TemplateService:
    return TemplateService(TemplateRepository(session), TemplateElementService(TemplateElementRepository(session)))

def get_parser_service() -> DedocTemplateParser:
    return DedocTemplateParser()