import os
from datetime import datetime
from typing import Optional

import requests
import structlog
from pylti1p3.exception import LtiException
from pylti1p3.grade import Grade
from pylti1p3.lineitem import LineItem
from pylti1p3.message_launch import MessageLaunch
from pylti1p3.service_connector import REQUESTS_USER_AGENT

from lti.exceptions import AgsNotSupportedException
from template.schemas.template import TemplateStructure

logger = structlog.get_logger(__name__)


class AgsService:
    """
    Служебные методы для работы с линиями оценок LTI AGS.
    Методы по обновлению и удалению линии реализованы как часть отсутствующего функционала в библиотеке
    и должны быть заменены на методы библиотеки при их появлении.
    https://github.com/dmitry-viskov/pylti1.3/pull/125
    """

    def __init__(self, message_launch: MessageLaunch, logger=structlog.get_logger(__name__)):
        if not message_launch.has_ags():
            raise AgsNotSupportedException()

        self.message_launch = message_launch
        self.ags = self.message_launch.get_ags()
        self.logger = log or logger

    def create_lineitem(self, template: TemplateStructure) -> Optional[LineItem]:
        if template.is_draft:
            self.logger.debug(
                "ags.create_lineitem.skip_draft",
                template_id=str(template.id),
            )
            return None

        return self.find_or_create_lineitem(template)

    def find_or_create_lineitem(self, template: TemplateStructure) -> Optional[LineItem]:
        lineitem = self._build_lineitem_object(template)
        return self.ags.find_or_create_lineitem(lineitem, "resource_id")

    def update_lineitem(self, template: TemplateStructure) -> None:
        lineitem = self.find_or_create_lineitem(template)
        if not lineitem:
            self.logger.warning(
                "ags.update_lineitem.not_found",
                template_id=str(template.id),
            )
            return

        original_values = lineitem.get_value()

        if lineitem.get_score_maximum() != template.max_score:
            lineitem.set_score_maximum(template.max_score)
        if lineitem.get_label() != template.name:
            lineitem.set_label(template.name)

        if original_values == lineitem.get_value():
            self.logger.debug(
                "ags.update_lineitem.no_changes",
                template_id=str(template.id),
            )
            return

        self._execute_request(
            method="PUT",
            url=lineitem.get_id(),
            data=lineitem.get_value(),
        )
        self.logger.info(
            "ags.update_lineitem.ok",
            template_id=str(template.id),
        )

    def delete_lineitem(self, template_id) -> None:
        lineitem = self.ags.find_lineitem_by_resource_id(str(template_id))

        if not lineitem:
            self.logger.warning(
                "ags.delete_lineitem.not_found",
                template_id=str(template_id),
            )
            return

        self._execute_request(method="DELETE", url=lineitem.get_id())
        self.logger.info(
            "ags.delete_lineitem.ok",
            template_id=str(template_id),
        )

    def set_grade(self, template: TemplateStructure, user_id: str, teacher_grade: float) -> None:
        lineitem = self.find_or_create_lineitem(template)
        if not lineitem:
            self.logger.warning(
                "ags.set_grade.no_lineitem",
                template_id=str(template.id),
                user_id=user_id,
            )
            return

        grade = (
            Grade()
            .set_score_given(teacher_grade)
            .set_score_maximum(template.max_score)
            .set_user_id(user_id)
            .set_timestamp(datetime.now().strftime("%Y-%m-%dT%H:%M:%S+0000"))
            .set_activity_progress("Completed")
            .set_grading_progress("FullyGraded")
        )

        self.ags.put_grade(grade, lineitem)
        self.logger.info(
            "ags.set_grade.ok",
            template_id=str(template.id),
            user_id=user_id,
            score=teacher_grade,
        )

    def _execute_request(self, method: str, url: str, data: Optional[dict] = None) -> None:
        with requests.Session() as session:
            try:
                response = session.request(
                    method,
                    url,
                    headers=self._build_ags_request_headers(),
                    json=data,
                )
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                self.logger.error(
                    "ags.request.error",
                    method=method,
                    url=url,
                    error=str(e),
                )
                raise LtiException(f"Ошибка LMS: {e}") from e

    def _build_lineitem_object(self, template: TemplateStructure) -> LineItem:
        return LineItem(
            {
                "label": template.name,
                "scoreMaximum": template.max_score,
                "resourceId": str(template.id),
                "submissionReview": self._build_submission_review(),
            }
        )

    def _build_submission_review(self) -> dict:
        public_backend_url = os.getenv("PUBLIC_BACKEND_URL", "").rstrip("/")

        review = {
            "label": "Открыть работу",
        }

        if public_backend_url:
            review["url"] = f"{public_backend_url}/api/v1/lti/launch"

        return review

    def _build_ags_request_headers(self) -> dict:
        service_data = self.message_launch.get_launch_data().get(
            "https://purl.imsglobal.org/spec/lti-ags/claim/endpoint"
        )
        access_token = self.message_launch.get_service_connector().get_access_token(
            service_data["scope"]
        )

        return {
            "User-Agent": REQUESTS_USER_AGENT,
            "Content-Type": "application/vnd.ims.lis.v2.lineitem+json",
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.ims.lis.v2.lineitem+json",
        }