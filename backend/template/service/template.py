from __future__ import annotations

import uuid

from core.auth.user_model import User
from lti.services.course import CourseService
from template.exceptions import InvalidTransitionException, InvalidCourseAccessDeniedException, \
    TemplateNotFoundException
from template.models.template import Template
from template.repository.template import TemplateRepository
from template.schemas.template import (
    TemplateCreationResponse,
    TemplateUpdateRequest,
    TemplateDetailResponse,
    TemplateCourseCollection,
)
from template.schemas.template_element import TemplatePatchRequest
from template.service.template_element import TemplateElementService
from lti.services.ags import AgsService
from files.services.hybrid_storage import HybridStorage


class TemplateAccessVerifier:
    def __init__(self, template: Template):
        self.template = template

    def is_valid_course(self, user: User):
        if self.template.course_id != user.course_id:
            raise InvalidCourseAccessDeniedException()
        return self

    def can_publish(self):
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
            patches: list[TemplatePatchRequest]
    ) -> TemplateCreationResponse:
        """Создает новый шаблон из файла"""
        template = Template(
            course_id=user.course_id,
            user_id=user.id,
            name=name
        )
        template = await self.repository.create(template)
        await self.elements_service.apply_patches(template.id, patches)
        return TemplateCreationResponse(id=template.id)


    async def get(self, user: User, template_id: uuid.UUID) -> TemplateDetailResponse:
        template = await self.repository.get(user.course_id, template_id)
        if not template:
            raise TemplateNotFoundException()

        TemplateAccessVerifier(template).is_valid_course(user)

        tree = self.elements_service.build_tree(template.elements)
        return TemplateDetailResponse.from_domain(template, user, tree)

    async def get_all_by_course(
            self,
            user: User,
            course_service: CourseService,
            include_drafts: bool = True
    ) -> TemplateCourseCollection:
        """Получает все шаблоны курса"""
        templates = await self.repository.get_all_by_course(
            user.course_id,
            include_drafts
        )
        return TemplateCourseCollection.from_domain(templates, user, course_service.name)

    async def update(
            self,
            user: User,
            template_id: uuid.UUID,
            modifiers: TemplateUpdateRequest
    ) -> None:
        """Обновляет информацию о шаблоне"""
        template = await self.repository.get(user.course_id, template_id)
        if not template:
            raise ValueError("Шаблон не найден")

        TemplateAccessVerifier(template).is_valid_course(user)

        if modifiers.name:
            template.name = modifiers.name
        if modifiers.max_score:
            template.max_score = modifiers.max_score

        if modifiers.elements and modifiers.elements.patches:
            await self.elements_service.apply_patches(template.id, modifiers.elements.patches)

        await self.repository.update(template)

    async def publish(
            self,
            user: User,
            template_id: uuid.UUID,
            ags_service: AgsService
    ) -> None:
        """Публикует шаблон (делает его доступным для студентов)"""
        template = await self.repository.get(user.course_id, template_id)
        if not template:
            raise ValueError("Шаблон не найден")

        TemplateAccessVerifier(template).is_valid_course(user).can_publish()

        template.is_draft = False
        await self.repository.update(template)
        ags_service.create_lineitem(template)

    async def delete(
            self,
            user: User,
            template_id: uuid.UUID,
            file_storage: HybridStorage,
            ags_service: AgsService
    ) -> None:
        template = await self.repository.get(user.course_id, template_id)
        if not template:
            raise TemplateNotFoundException(template_id)

        TemplateAccessVerifier(template).is_valid_course(user)

        media_keys = [
            el.properties["media_key"]
            for el in template.elements
            if el.properties and "media_key" in el.properties
        ]

        await self.repository.delete(template)

        if media_keys:
            file_storage.delete_many(media_keys)
        ags_service.delete_lineitem(template_id)

    async def publish_many(
                self,
                user: User,
                template_ids: list[uuid.UUID],
                ags_service: AgsService
        ) -> None:
        templates = await self.repository.get_many(user.course_id, template_ids)
        if not templates:
            return

        for template in templates:
            TemplateAccessVerifier(template).is_valid_course(user).can_publish()
            template.is_draft = False

        await self.repository.session.flush()

        for template in templates:
            ags_service.create_lineitem(template)

    async def delete_many(
            self,
            user: User,
            template_ids: list[uuid.UUID],
            file_storage: HybridStorage,
            ags_service: AgsService
    ) -> None:
        templates = await self.repository.get_many(user.course_id, template_ids)
        if not templates:
            return

        for template in templates:
            TemplateAccessVerifier(template).is_valid_course(user)

        media_keys_to_delete = []
        for template in templates:
            keys = await self.elements_service.get_media_keys(template.id)
            media_keys_to_delete.extend(keys)

        await self.repository.delete_many(user.course_id, templates)

        for template in templates:
            ags_service.delete_lineitem(template.id)

        # if media_keys_to_delete:
        #     file_storage.delete_many(media_keys_to_delete)