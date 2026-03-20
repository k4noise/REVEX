import os
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, UploadFile, File, status
from fastapi.responses import Response, JSONResponse
from fastapi_hypermodel import HALResponse

from core.auth.depedency import get_user_with_any_role, get_user
from core.files.depedency import get_file_storage
from core.files.services.hybrid_storage import HybridStorage
from core.auth.user_model import UserRole, User
from lti.depedencies import get_ags_service
from lti.services.ags import AgsService
from template.depedencies import get_template_service, get_parser_service

from template.schemas.template import (
    TemplateCreationResponse,
    TemplateUpdateRequest,
    TemplateDetailResponse,
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
        patches = parser_service.parse(tmp_path)
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


@router.get(
    "/{template_id}",
    response_model=TemplateDetailResponse,
    response_class=HALResponse,
)
async def get_template(
        template_id: uuid.UUID,
        user: User = Depends(get_user),
        template_service: TemplateService = Depends(get_template_service),
):
    return await template_service.get(user, template_id)


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