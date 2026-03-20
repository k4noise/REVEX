from __future__ import annotations

import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.user_model import User
from template.exceptions import InvalidTransitionException, InvalidCourseAccessDeniedException
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
from core.files.services.hybrid_storage import HybridStorage


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
            session: AsyncSession
    ):
        self.repository = repository
        self.elements_service = elements_service
        self.session = session

    async def create_from_file(
            self,
            user: User,
            name: str,
            patches: list[TemplatePatchRequest]
    ) -> TemplateCreationResponse:
        """Создает новый шаблон из файла"""
        template = Template(
            course_id=user.course_id,
            user_id=user.sub,
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
            include_drafts: bool = True
    ) -> TemplateCourseCollection:
        """Получает все шаблоны курса"""
        templates = await self.repository.get_all_by_course(
            user.course_id,
            include_drafts
        )
        return TemplateCourseCollection.from_domain(templates, user, user.course_name)

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
        await ags_service.create_lineitem({
            "label": template.name,
            "scoreMaximum": template.max_score
        })

    async def delete(
            self,
            user: User,
            template_id: uuid.UUID,
            file_storage: HybridStorage,
            ags_service: AgsService
    ) -> None:
        template = await self.repository.get(user.course_id, template_id)
        if not template:
            raise TemplateNotFoundException()

        TemplateAccessVerifier(template).is_valid_course(user)

        media_keys = [
            el.properties["media_key"]
            for el in template.elements
            if el.properties and "media_key" in el.properties
        ]

        await self.repository.delete(template)

        if media_keys:
            await file_storage.delete_many(media_keys)
        await ags_service.delete_lineitem(template_id)