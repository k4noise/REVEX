from __future__ import annotations

import uuid

import structlog

from core.auth.user_model import User
from core.background_service import BackgroundTaskService
from files.services.hybrid_storage import HybridStorage
from lti.jobs import ags_create_lineitem_job, ags_delete_lineitem_job
from lti.services.course import CourseService
from template.exceptions import (
    InvalidTransitionException,
    InvalidCourseAccessDeniedException,
    TemplateNotFoundException,
)
from template.models.template import Template
from template.repository.template import TemplateRepository
from template.schemas.template import (
    TemplateCreationResponse,
    TemplateUpdateRequest,
    TemplateDetailResponse,
    TemplateCourseCollection,
)
from template.schemas.template_element import AnyPatch
from template.services.template_element import TemplateElementService

logger = structlog.get_logger(__name__)


class TemplateAccessVerifier:
    def __init__(self, template: Template):
        self.template = template

    def is_valid_course(self, user: User) -> "TemplateAccessVerifier":
        if self.template.course_id != user.course_id:
            raise InvalidCourseAccessDeniedException()
        return self

    def can_publish(self) -> "TemplateAccessVerifier":
        if not self.template.is_draft:
            raise InvalidTransitionException()
        return self


class TemplateService:
    def __init__(
            self,
            repository: TemplateRepository,
            elements_service: TemplateElementService,
    ):
        self.repository = repository
        self.elements_service = elements_service


    async def create_from_file(
            self,
            user: User,
            name: str,
            patches: list[AnyPatch],
    ) -> TemplateCreationResponse:
        logger.info(
            "template.create_from_file.start",
            template_name=name,
        )

        template = Template(
            course_id=user.course_id,
            user_id=user.id,
            name=name,
        )
        template = await self.repository.create(template)
        await self.elements_service.apply_patches(template.id, patches)

        logger.info(
            "template.create_from_file.ok",
            template_id=str(template.id),
        )

        return TemplateCreationResponse(id=template.id)

    async def get(self, user: User, template_id: uuid.UUID) -> TemplateDetailResponse:
        template = await self.repository.get(user.course_id, template_id)
        if not template:
            logger.warning(
                "template.get.not_found",
                template_id=str(template_id),
            )
            raise TemplateNotFoundException(template_id)

        TemplateAccessVerifier(template).is_valid_course(user)

        tree = self.elements_service.build_tree(template.elements)
        return TemplateDetailResponse.from_domain(template, user, tree)

    async def get_all_by_course(
            self,
            user: User,
            course_service: CourseService,
            include_drafts: bool = True,
    ) -> TemplateCourseCollection:
        if not user.is_teacher():
            templates = await self.repository.get_all_by_course_with_reports(
                course_id=user.course_id,
                user_id=user.id,
                include_drafts=include_drafts,
            )
        else:
            templates = await self.repository.get_all_by_course(
                course_id=user.course_id,
                include_drafts=include_drafts,
            )

        logger.info(
            "template.get_all_by_course.ok",
            course_id=user.course_id,
            template_count=len(templates),
        )

        return TemplateCourseCollection.from_domain(
            templates,
            user,
            course_service.name,
        )

    async def update(
            self,
            user: User,
            template_id: uuid.UUID,
            modifiers: TemplateUpdateRequest,
    ) -> None:
        logger.info(
            "template.update.start",
            template_id=str(template_id),
        )

        template = await self.repository.get(user.course_id, template_id)
        if not template:
            logger.warning(
                "template.update.not_found",
                template_id=str(template_id),
            )
            raise TemplateNotFoundException(template_id)

        TemplateAccessVerifier(template).is_valid_course(user)

        if modifiers.name is not None:
            template.name = modifiers.name
        if modifiers.max_score is not None:
            template.max_score = modifiers.max_score

        if modifiers.elements and modifiers.elements.patches:
            await self.elements_service.apply_patches(
                template.id,
                modifiers.elements.patches,
            )

        await self.repository.update(template)

        logger.info(
            "template.update.ok",
            template_id=str(template_id),
        )


    async def publish(
            self,
            user: User,
            template_id: uuid.UUID,
            background_service: BackgroundTaskService,
    ) -> None:
        logger.info(
            "template.publish.start",
            template_id=str(template_id),
        )

        template = await self.repository.get(user.course_id, template_id)
        if not template:
            logger.warning(
                "template.publish.not_found",
                template_id=str(template_id),
            )
            raise TemplateNotFoundException(template_id)

        TemplateAccessVerifier(template).is_valid_course(user).can_publish()

        template.is_draft = False
        await self.repository.update(template)

        try:
            background_service.enqueue(
                ags_create_lineitem_job,
                user.launch_id,
                str(template.id),
            )
        except Exception:
            logger.exception(
                "template.publish.enqueue_ags_failed",
                template_id=str(template_id),
            )
            raise

        logger.info(
            "template.publish.ok",
            template_id=str(template_id),
        )

    async def delete(
            self,
            user: User,
            template_id: uuid.UUID,
            file_storage: HybridStorage,
            background_service: BackgroundTaskService,
    ) -> None:
        logger.info(
            "template.delete.start",
            template_id=str(template_id),
        )

        template = await self.repository.get(user.course_id, template_id)
        if not template:
            logger.warning(
                "template.delete.not_found",
                template_id=str(template_id),
            )
            raise TemplateNotFoundException(template_id)

        TemplateAccessVerifier(template).is_valid_course(user)

        media_keys = [
            el.properties["media_key"]
            for el in template.elements
            if el.properties and "media_key" in el.properties
        ]

        await self.repository.delete(template)

        if media_keys:
            deleted = file_storage.delete_many(media_keys)
            logger.info(
                "template.delete.files",
                template_id=str(template_id),
                media_key_count=len(media_keys),
                deleted_count=deleted,
            )

        try:
            background_service.enqueue(
                ags_delete_lineitem_job,
                user.launch_id,
                str(template_id),
            )
        except Exception:
            logger.exception(
                "template.delete.enqueue_ags_delete_failed",
                template_id=str(template_id),
            )

        logger.info(
            "template.delete.ok",
            template_id=str(template_id),
        )

    async def publish_many(
            self,
            user: User,
            template_ids: list[uuid.UUID],
            background_service: BackgroundTaskService,
    ) -> None:
        logger.info(
            "template.publish_many.start",
            template_ids=[str(tid) for tid in template_ids],
        )

        templates = await self.repository.get_many(user.course_id, template_ids)
        if not templates:
            logger.info(
                "template.publish_many.empty",
                course_id=user.course_id,
            )
            return

        for template in templates:
            TemplateAccessVerifier(template).is_valid_course(user).can_publish()
            template.is_draft = False

        await self.repository.session.flush()

        for template in templates:
            try:
                background_service.enqueue(
                    ags_create_lineitem_job,
                    user.launch_id,
                    str(template.id),
                )
            except Exception:
                logger.exception(
                    "template.publish_many.enqueue_ags_failed",
                    template_id=str(template.id),
                )

        logger.info(
            "template.publish_many.ok",
            published_count=len(templates),
        )

    async def delete_many(
            self,
            user: User,
            template_ids: list[uuid.UUID],
            file_storage: HybridStorage,
            background_service: BackgroundTaskService,
    ) -> None:
        logger.info(
            "template.delete_many.start",
            template_ids=[str(tid) for tid in template_ids],
        )

        templates = await self.repository.get_many(user.course_id, template_ids)
        if not templates:
            logger.info(
                "template.delete_many.empty",
                course_id=user.course_id,
            )
            return

        for template in templates:
            TemplateAccessVerifier(template).is_valid_course(user)

        media_keys_to_delete: list[str] = []
        for template in templates:
            keys = await self.elements_service.get_media_keys(template.id)
            media_keys_to_delete.extend(keys)

        await self.repository.delete_many(user.course_id, templates)

        if media_keys_to_delete:
            deleted = file_storage.delete_many(media_keys_to_delete)
            logger.info(
                "template.delete_many.files",
                deleted_count=deleted,
                media_key_count=len(media_keys_to_delete),
            )

        for template in templates:
            try:
                background_service.enqueue(
                    ags_delete_lineitem_job,
                    user.launch_id,
                    str(template.id),
                )
            except Exception:
                logger.exception(
                    "template.delete_many.enqueue_ags_delete_failed",
                    template_id=str(template.id),
                )

        logger.info(
            "template.delete_many.ok",
            deleted_count=len(templates),
        )