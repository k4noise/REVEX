import uuid
from typing import Sequence

import structlog
from sqlalchemy import Select, update, select, case, type_coerce, JSON
from sqlalchemy.ext.asyncio import AsyncSession

from answer.exceptions import AnswerPatchException
from answer.model import Answer
from answer.schemas import (
    UpdateAnswerDataRequest,
    NewAnswerData,
    UpdateAnswerScoresRequest,
    PreGradedAnswerResponse,
)

logger = structlog.get_logger(__name__)


class AnswerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_by_report(self, report_id: uuid.UUID) -> Sequence[Answer]:
        query: Select = select(Answer).where(Answer.report_id == report_id)
        result = await self.session.execute(query)
        answers = result.scalars().all()
        logger.info(
            "answers.list.by_report",
            report_id=str(report_id),
            count=len(answers),
        )
        return answers

    async def bulk_create(
            self,
            report_id: uuid.UUID,
            answers_data: Sequence[NewAnswerData],
    ) -> list[uuid.UUID]:
        if not answers_data:
            logger.info("answers.bulk_create.empty", report_id=str(report_id))
            return []

        answers = [
            Answer(
                report_id=report_id,
                element_id=answer_data.element_id,
                score=answer_data.score,
                data=answer_data.data,
                pre_grade=answer_data.pre_grade,
            )
            for answer_data in answers_data
        ]
        self.session.add_all(answers)
        await self.session.flush()

        ids = [answer.id for answer in answers]
        logger.info(
            "answers.bulk_create.ok",
            report_id=str(report_id),
            created_count=len(ids),
        )
        return ids

    async def bulk_update_data(
            self,
            report_id: uuid.UUID,
            answers_data: Sequence[UpdateAnswerDataRequest],
    ) -> int:
        if not answers_data:
            logger.info("answers.bulk_update_data.empty", report_id=str(report_id))
            return 0

        answer_ids: list[uuid.UUID] = []
        data_updates: dict[uuid.UUID, dict | None] = {}

        for item in answers_data:
            answer_ids.append(item.id)
            data_updates[item.id] = item.data

        data_updates_serialized = {
            k: type_coerce(v, JSON)
            for k, v in data_updates.items()
        }

        data_case_expr = case(
            data_updates_serialized,
            value=Answer.id,
            else_=Answer.data,
        )

        statement = (
            update(Answer)
            .where(
                Answer.report_id == report_id,
                Answer.id.in_(answer_ids),
                )
            .values(
                data=data_case_expr,
                score=None,
                pre_grade=None,
            )
        )

        result = await self.session.execute(statement)
        updated = result.rowcount or 0

        if updated != len(answer_ids):
            logger.warning(
                "answers.bulk_update_data.partial",
                report_id=str(report_id),
                requested=len(answer_ids),
                updated=updated,
            )
            raise AnswerPatchException(
                "некоторые ответы не найдены или не принадлежат указанному отчету"
            )

        logger.info(
            "answers.bulk_update_data.ok",
            report_id=str(report_id),
            updated=updated,
        )
        return updated

    async def bulk_update_scores(
            self,
            report_id: uuid.UUID,
            scores: Sequence[UpdateAnswerScoresRequest],
    ) -> int:
        if not scores:
            logger.info("answers.bulk_update_scores.empty", report_id=str(report_id))
            return 0

        answer_ids: list[uuid.UUID] = []
        score_updates: dict[uuid.UUID, float | None] = {}

        for item in scores:
            answer_ids.append(item.id)
            score_updates[item.id] = item.score

        score_case_expr = case(
            score_updates,
            value=Answer.id,
            else_=Answer.score,
        )

        statement = (
            update(Answer)
            .where(
                Answer.report_id == report_id,
                Answer.id.in_(answer_ids),
                )
            .values(score=score_case_expr)
        )

        result = await self.session.execute(statement)
        updated = result.rowcount or 0

        if updated != len(answer_ids):
            logger.warning(
                "answers.bulk_update_scores.partial",
                report_id=str(report_id),
                requested=len(answer_ids),
                updated=updated,
            )
            raise AnswerPatchException(
                "некоторые ответы не найдены или не принадлежат указанному отчету"
            )

        logger.info(
            "answers.bulk_update_scores.ok",
            report_id=str(report_id),
            updated=updated,
        )
        return updated

    async def bulk_update_pre_grade(
            self,
            report_id: uuid.UUID,
            graded_answers: Sequence[PreGradedAnswerResponse],
    ) -> int:
        if not graded_answers:
            logger.info(
                "answers.bulk_update_pre_grade.empty",
                report_id=str(report_id),
            )
            return 0

        answer_ids: list[uuid.UUID] = []
        pregrade_updates: dict[uuid.UUID, dict | None] = {}

        for ga in graded_answers:
            answer_ids.append(ga.id)
            pregrade_updates[ga.id] = ga.pre_grade


        pregrade_updates_serialized = {
            k: type_coerce(v, JSON)
            for k, v in pregrade_updates.items()
        }

        pregrade_case_expr = case(
            pregrade_updates_serialized,
            value=Answer.id,
            else_=Answer.pre_grade,
        )

        statement = (
            update(Answer)
            .where(
                Answer.report_id == report_id,
                Answer.id.in_(answer_ids),
                )
            .values(pre_grade=pregrade_case_expr)
        )

        result = await self.session.execute(statement)
        updated = result.rowcount or 0

        if updated != len(answer_ids):
            logger.warning(
                "answers.bulk_update_pre_grade.partial",
                report_id=str(report_id),
                requested=len(answer_ids),
                updated=updated,
            )
            raise AnswerPatchException(
                "некоторые ответы не найдены или не принадлежат указанному отчету"
            )

        logger.info(
            "answers.bulk_update_pre_grade.ok",
            report_id=str(report_id),
            updated=updated,
        )
        return updated