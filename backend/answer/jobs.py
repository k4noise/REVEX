from __future__ import annotations

import asyncio
import uuid
from typing import Sequence, Dict, List, Optional

import structlog

from answer.services.pre_grader import PreGraderService
from answer.repository import AnswerRepository
from answer.services.answer import AnswerService
from answer.services.param_map import ParameterMapBuilder
from answer.services.explainer import PregradeExplainerService
from core.auth.user_model import User, UserRole
from core.db import AsyncSessionLocal
from report.repository import ReportRepository
from template.schemas.template import FullWorkResponse
from template.schemas.template_element import TemplateElementResponse, ElementType

logger = structlog.get_logger(__name__)


def pre_grade_report_job(report_id_str: str) -> None:
    report_id = uuid.UUID(report_id_str)
    asyncio.run(_pre_grade_report_async(report_id))


async def _pre_grade_report_async(report_id: uuid.UUID) -> None:
    logger.info(
        "pre_grade.start",
        report_id=str(report_id),
    )

    async with AsyncSessionLocal() as session:
        try:
            report_repo = ReportRepository(session)
            answer_repo = AnswerRepository(session)
            answer_service = AnswerService(answer_repo)

            report = await report_repo.get_with_template_and_answers(report_id)
            if report is None:
                logger.warning(
                    "pre_grade.report_not_found",
                    report_id=str(report_id),
                )
                return

            fake_user = User(
                id="pregrader",
                roles=[UserRole.TEACHER],
                launch_id="",
                course_id=report.template.course_id,
            )

            dto = FullWorkResponse.from_domain(
                report,
                fake_user,
                nrps=None,
            )

            parameters = ParameterMapBuilder.build(
                answers=dto.answers,
                template_elements=dto.template.elements,
            )

            results = PreGraderService(
                dto.answers,
                parameters=parameters,
            ).grade_all()

            question_text_map = _build_question_text_map(dto.template.elements)
            explainer = PregradeExplainerService()

            for result in results:
                if not result.pre_grade:
                    continue

                explanation = explainer.generate(
                    result,
                    question_text=question_text_map.get(str(result.element_id)),
                )
                if explanation:
                    result.pre_grade["explanation"] = explanation

            await answer_service.update_pre_grade(report.id, results)
            await session.commit()

            logger.info(
                "pre_grade.ok",
                report_id=str(report_id),
                graded_count=len(results),
            )
        except Exception:
            await session.rollback()
            logger.exception(
                "pre_grade.failed",
                report_id=str(report_id),
            )


def _build_question_text_map(
        elements_tree: Sequence[TemplateElementResponse],
) -> dict[str, str]:
    elements = _flatten_elements(elements_tree)
    by_id = {element.id: element for element in elements}
    children = _build_children_index(elements)

    result: dict[str, str] = {}
    for element in elements:
        if element.type != ElementType.ANSWER:
            continue

        question = _find_nearest_ancestor_of_type(
            element.id,
            ElementType.QUESTION,
            by_id,
        )
        question_text = _get_question_text(question, children) or ""
        result[str(element.id)] = question_text

    return result


def _flatten_elements(
        elements: Sequence[TemplateElementResponse],
) -> list[TemplateElementResponse]:
    result: list[TemplateElementResponse] = []
    seen: set[uuid.UUID] = set()

    def walk(node: TemplateElementResponse) -> None:
        if node.id in seen:
            return

        seen.add(node.id)
        result.append(node)

        for child in node.children or []:
            walk(child)

    for element in elements or []:
        walk(element)

    return result


def _build_children_index(
        elements: Sequence[TemplateElementResponse],
) -> Dict[uuid.UUID, List[TemplateElementResponse]]:
    children: Dict[uuid.UUID, List[TemplateElementResponse]] = {}
    for el in elements:
        if el.parent_element_id:
            children.setdefault(el.parent_element_id, []).append(el)
    return children


def _find_nearest_ancestor_of_type(
        element_id: uuid.UUID,
        target_type: ElementType,
        by_id: Dict[uuid.UUID, TemplateElementResponse],
) -> Optional[TemplateElementResponse]:
    current = by_id.get(element_id)
    visited: set[uuid.UUID] = set()

    while current and current.parent_element_id:
        parent_id = current.parent_element_id
        if parent_id in visited:
            break

        visited.add(parent_id)
        parent = by_id.get(parent_id)
        if not parent:
            break

        if parent.type == target_type:
            return parent

        current = parent

    return None


def _get_question_text(
        question: Optional[TemplateElementResponse],
        children_index: Dict[uuid.UUID, List[TemplateElementResponse]],
) -> Optional[str]:
    if not question:
        return None

    if question.data and question.data.strip():
        return question.data.strip()

    for child in children_index.get(question.id, []):
        if child.type == ElementType.TEXT and child.data and child.data.strip():
            return child.data.strip()

    return None