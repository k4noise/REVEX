import uuid
from typing import Sequence

import structlog

from answer.repository import AnswerRepository
from answer.schemas import (
    NewAnswerData,
    UpdateAnswerDataRequest,
    UpdateAnswerScoresRequest,
    PreGradedAnswerResponse,
)

logger = structlog.get_logger(__name__)


class AnswerService:
    def __init__(self, repository: AnswerRepository):
        self.repository = repository

    async def create(
            self,
            report_id: uuid.UUID,
            elements: Sequence[NewAnswerData],
    ) -> list[uuid.UUID]:
        logger.info(
            "answers.create.start",
            report_id=str(report_id),
            count=len(elements),
        )
        ids = await self.repository.bulk_create(report_id, elements)
        logger.info(
            "answers.create.ok",
            report_id=str(report_id),
            created_count=len(ids),
        )
        return ids

    async def update_data(
            self,
            report_id: uuid.UUID,
            answers: Sequence[UpdateAnswerDataRequest],
    ) -> int:
        logger.info(
            "answers.update_data.start",
            report_id=str(report_id),
            count=len(answers),
        )
        updated = await self.repository.bulk_update_data(report_id, answers)
        logger.info(
            "answers.update_data.ok",
            report_id=str(report_id),
            updated=updated,
        )
        return updated

    async def update_scores(
            self,
            report_id: uuid.UUID,
            scores: Sequence[UpdateAnswerScoresRequest],
    ) -> int:
        logger.info(
            "answers.update_scores.start",
            report_id=str(report_id),
            count=len(scores),
        )
        updated = await self.repository.bulk_update_scores(report_id, scores)
        logger.info(
            "answers.update_scores.ok",
            report_id=str(report_id),
            updated=updated,
        )
        return updated

    async def update_pre_grade(
            self,
            report_id: uuid.UUID,
            graded_answers: Sequence[PreGradedAnswerResponse],
    ) -> int:
        logger.info(
            "answers.update_pre_grade.start",
            report_id=str(report_id),
            count=len(graded_answers),
        )
        updated = await self.repository.bulk_update_pre_grade(report_id, graded_answers)
        logger.info(
            "answers.update_pre_grade.ok",
            report_id=str(report_id),
            updated=updated,
        )
        return updated