import os
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, UploadFile, File, status
from fastapi.responses import Response, JSONResponse
from fastapi.concurrency import run_in_threadpool
from fastapi_hypermodel import HALResponse

from core.auth.depedency import get_user_with_any_role, get_user
from files.depedency import get_file_storage
from files.services.hybrid_storage import HybridStorage
from core.auth.user_model import UserRole, User
from lti.depedencies import get_ags_service, get_course_service
from lti.services.ags import AgsService
from lti.services.course import CourseService
from template.depedencies import get_template_service, get_parser_service

from template.schemas.template import (
    TemplateCreationResponse,
    TemplateUpdateRequest,
    TemplateDetailResponse,
    TemplateCourseCollection, TemplateManyRequest,
)
from template.service.parser import DedocTemplateParser
from template.service.template import TemplateService

router = APIRouter(prefix="/templates", tags=["Template"])


@router.post(
    "",
    response_model=TemplateCreationResponse,
    response_class=HALResponse,
    status_code=status.HTTP_201_CREATED,
)
async def parse_template(
        template: UploadFile = File(..., description="DOCX файл для обработки"),
        user: User = Depends(get_user_with_any_role(UserRole.TEACHER)),
        template_service: TemplateService = Depends(get_template_service),
        parser_service: DedocTemplateParser = Depends(get_parser_service),
):
    suffix = Path(template.filename).suffix if template.filename else ""
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await template.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        patches = await run_in_threadpool(parser_service.parse, tmp_path)

        return await template_service.create_from_file(
            user=user,
            name=template.filename,
            patches=patches,
        )
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


@router.get(
    "",
    response_model=TemplateCourseCollection,
    response_class=HALResponse,
    summary="Получить все шаблоны курса",
)
async def get_templates(
        user: User = Depends(get_user),
        course_service: CourseService = Depends(get_course_service),
        template_service: TemplateService = Depends(get_template_service),
):
    include_drafts = UserRole.TEACHER in user.roles
    return await template_service.get_all_by_course(user, course_service, include_drafts)


@router.get(
    "/{template_id}",
    response_model=TemplateDetailResponse,
    response_class=HALResponse,
    response_model_exclude_none=True
)
async def get_template(
        template_id: uuid.UUID,
        user: User = Depends(get_user),
        template_service: TemplateService = Depends(get_template_service),
):
    return await template_service.get(user, template_id)


@router.patch("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def save_modified_template(
        template_id: uuid.UUID,
        modified_template: TemplateUpdateRequest,
        user: User = Depends(get_user_with_any_role(UserRole.TEACHER)),
        template_service: TemplateService = Depends(get_template_service),
):
    await template_service.update(user, template_id, modified_template)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{template_id}/publish", status_code=status.HTTP_204_NO_CONTENT)
async def publish_template(
        template_id: uuid.UUID,
        user: User = Depends(get_user_with_any_role(UserRole.TEACHER)),
        template_service: TemplateService = Depends(get_template_service),
        ags_service: AgsService = Depends(get_ags_service),
):
    await template_service.publish(user, template_id, ags_service)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{template_id}")
async def remove_template(
        template_id: uuid.UUID,
        user: User = Depends(get_user_with_any_role(UserRole.TEACHER)),
        template_service: TemplateService = Depends(get_template_service),
        ags_service: AgsService = Depends(get_ags_service),
        file_storage: HybridStorage = Depends(get_file_storage),
):
    await template_service.delete(user, template_id, file_storage, ags_service)
    return JSONResponse({"detail": "Шаблон успешно удален"})

@router.post("/publish-many", status_code=status.HTTP_204_NO_CONTENT, name="publish_many_templates")
async def publish_many_templates(
        request: TemplateManyRequest,
        user: User = Depends(get_user_with_any_role(UserRole.TEACHER)),
        template_service: TemplateService = Depends(get_template_service),
        ags_service: AgsService = Depends(get_ags_service),
):
    """Массово публикует шаблоны"""
    await template_service.publish_many(user, request.ids, ags_service)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/delete-many", status_code=status.HTTP_204_NO_CONTENT, name="delete_many_templates")
async def delete_many_templates(
        request: TemplateManyRequest,
        user: User = Depends(get_user_with_any_role(UserRole.TEACHER)),
        template_service: TemplateService = Depends(get_template_service),
        ags_service: AgsService = Depends(get_ags_service),
        file_storage: HybridStorage = Depends(get_file_storage),
):
    """Массово удаляет шаблоны и их файлы"""
    await template_service.delete_many(user, request.ids, file_storage, ags_service)
    return Response(status_code=status.HTTP_204_NO_CONTENT)