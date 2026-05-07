import os
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, status
from fastapi.responses import Response, JSONResponse
from fastapi.concurrency import run_in_threadpool
from fastapi_hypermodel import HALResponse
from pylti1p3.message_launch import MessageLaunch

from core.auth.dependency import get_user_with_any_role, get_user
from core.background_service import BackgroundTaskService
from core.dependencies import get_background_task_service
from files.dependencies import get_file_storage
from files.services.hybrid_storage import HybridStorage
from core.auth.user_model import UserRole, User
from lti.dependencies import get_ags_service, get_course_service, get_launch_service, \
    get_message_launch
from lti.services.ags import AgsService
from lti.services.course import CourseService
from lti.services.launch import LaunchService
from report.dependencies import get_report_service
from report.schemas.report import ReportCreationResponse
from report.services.report import ReportService
from template.dependencies import get_template_service, get_parser_service

from template.schemas.template import (
    TemplateCreationResponse,
    TemplateUpdateRequest,
    TemplateDetailResponse,
    TemplateCourseCollection,
    TemplateManyRequest,
)
from template.services.parser import DedocTemplateParser
from template.services.template import TemplateService

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
            name=template.filename or "template",
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
    return await template_service.get_all_by_course(
        user,
        course_service,
        include_drafts,
    )


@router.get(
    "/{template_id}",
    response_model=TemplateDetailResponse,
    response_class=HALResponse,
    response_model_exclude_none=True,
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
        background_service: BackgroundTaskService = Depends(get_background_task_service),
        template_service: TemplateService = Depends(get_template_service),
):
    await template_service.publish(
        user,
        template_id,
        background_service,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{template_id}")
async def remove_template(
        template_id: uuid.UUID,
        user: User = Depends(get_user_with_any_role(UserRole.TEACHER)),
        template_service: TemplateService = Depends(get_template_service),
        background_service: BackgroundTaskService = Depends(get_background_task_service),
        file_storage: HybridStorage = Depends(get_file_storage),
):
    await template_service.delete(
        user,
        template_id,
        file_storage,
        background_service,
    )
    return JSONResponse({"detail": "Шаблон успешно удален"})

@router.post(
    "/publish-many",
    status_code=status.HTTP_204_NO_CONTENT,
    name="publish_many_templates",
)
async def publish_many_templates(
        request: TemplateManyRequest,
        user: User = Depends(get_user_with_any_role(UserRole.TEACHER)),
        background_service: BackgroundTaskService = Depends(get_background_task_service),
        template_service: TemplateService = Depends(get_template_service),
        ags_service: AgsService = Depends(get_ags_service),
):
    await template_service.publish_many(
        user,
        request.ids,
        background_service,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/delete-many",
    status_code=status.HTTP_204_NO_CONTENT,
    name="delete_many_templates",
)
async def delete_many_templates(
        request: TemplateManyRequest,
        user: User = Depends(get_user_with_any_role(UserRole.TEACHER)),
        background_service: BackgroundTaskService = Depends(get_background_task_service),
        template_service: TemplateService = Depends(get_template_service),
        file_storage: HybridStorage = Depends(get_file_storage),
):
    await template_service.delete_many(
        user,
        request.ids,
        file_storage,
        background_service,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{template_id}/reports", response_model=ReportCreationResponse)
async def create_report(
        template_id: uuid.UUID,
        user: User = Depends(get_user_with_any_role(UserRole.STUDENT)),
        template_service: TemplateService = Depends(get_template_service),
        report_service: ReportService = Depends(get_report_service),
):
    template = await template_service.get(user, template_id)
    return await report_service.create(user, template)


@router.get(
    "/{template_id}/reports",
    response_class=HALResponse,
    response_model_exclude_none=True,
)
async def get_reports_by_template(
        template_id: uuid.UUID,
        author_id: Optional[str] = None,
        report_status: Optional[str] = None,
        user: User = Depends(get_user),
        template_service: TemplateService = Depends(get_template_service),
        report_service: ReportService = Depends(get_report_service),
        launch_service: LaunchService = Depends(get_launch_service),
        message_launch: MessageLaunch = Depends(get_message_launch)
):
    template = await template_service.get(user, template_id)
    if author_id and report_status:
        return await report_service.get_all_by_template_and_status(
            user,
            template,
            author_id,
            report_status,
            launch_service,
            message_launch
        )

    return await report_service.get_all_by_template(template, user, launch_service, message_launch)