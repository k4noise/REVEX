import uuid
from typing import Sequence

import structlog

from answer.jobs import pre_grade_report_job
from answer.schemas import AnswerResponse, UpdateAnswerScoresRequest
from core.auth.user_model import User
from core.background_service import BackgroundTaskService
from lti.jobs import ags_set_grade_job
from lti.services.nrps import NrpsService
from report.services.report import ReportService
from report.services.report_access_verifier import UpdateGradeInfo

logger = structlog.get_logger(__name__)


class GradeService:
    def __init__(
            self,
            report_service: ReportService,
            background_task_service: BackgroundTaskService,
            nrps_service: NrpsService,
            log=None,
    ):
        self.report_service = report_service
        self.background_task_service = background_task_service
        self.nrps_service = nrps_service
        self.logger = log or logger

    async def send_to_grade(self, user: User, report_id: uuid.UUID) -> None:
        self.logger.info(
            "grade.send_to_grade.start",
            report_id=str(report_id),
            user_id=user.id,
        )

        report = await self.report_service.get(user, report_id, self.nrps_service)

        self.background_task_service.enqueue(pre_grade_report_job, str(report_id))

        self.logger.info(
            "grade.send_to_grade.ok",
            report_id=str(report_id),
            status=report.status.value,
        )
        await self.report_service.submit(user, report_id)


    async def grade(
            self,
            user: User,
            report_id: uuid.UUID,
            scores: Sequence[UpdateAnswerScoresRequest],
    ) -> None:
        self.logger.info(
            "grade.grade.start",
            report_id=str(report_id),
            user_id=user.id,
            scores_count=len(scores),
        )

        report = await self.report_service.get(user, report_id, self.nrps_service)

        score_map = {score.id: score.score for score in scores}
        updated_answers: list[AnswerResponse] = [
            answer.model_copy(
                update={"score": score_map.get(answer.id, answer.score)}
            )
            for answer in report.answers
        ]

        final_score = await self._calc_final_score(
            updated_answers,
            report.template.max_score,
        )

        report_updates = UpdateGradeInfo(
            id=report_id,
            grader_id=user.id,
            new_scores=scores,
            final_score=final_score,
        )

        await self.report_service.grade(user, report_id, report_updates)

        self.background_task_service.enqueue(
            ags_set_grade_job,
            user.launch_id,
            str(report.template.id),
            report.author_id,
            final_score,
        )

        self.logger.info(
            "grade.grade.ok",
            report_id=str(report_id),
            final_score=final_score,
        )

    async def _calc_final_score(
            self,
            answers: Sequence[AnswerResponse],
            max_score: int,
    ) -> float:
        if not answers or max_score <= 0:
            return 0.0

        group_weights: dict[uuid.UUID | None, float] = {}

        for answer in answers:
            base_weight = answer.weight if answer.weight is not None else 1.0
            root_id = answer.root_id
            group_weights[root_id] = group_weights.get(root_id, 0.0) + base_weight

        total_weighted_score = 0.0
        total_weight = 0.0

        for answer in answers:
            base_weight = answer.weight if answer.weight is not None else 1.0
            root_id = answer.root_id
            group_weight = group_weights.get(root_id, base_weight)
            current_weight = base_weight / group_weight if group_weight else 0.0
            total_weighted_score += (answer.score or 0.0) * current_weight
            total_weight += current_weight

        if total_weight == 0.0:
            return 0.0

        normalized_score = total_weighted_score / total_weight
        return round(normalized_score * max_score, 2)