from typing import Optional

from fastapi import APIRouter, File, UploadFile, Depends
from fastapi_hypermodel import UrlFor, HALResponse
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel
from starlette.responses import Response, JSONResponse

from config.settings import USER_IMAGE_PREFIX
from core.halhypermodel import HALHyperModel
from files.dependencies import get_file_storage
from files.services.hybrid_storage import HybridStorage

router = APIRouter()


class FileResponse(HALHyperModel):
    media_key: str
    image_url: Optional[UrlFor] = UrlFor(
        "get_image",
        {"file_key": "<media_key>"},
        condition=lambda values: bool(values.get("media_key")),
    )

    model_config = ConfigDict(
        serialize_by_alias=True,
        populate_by_name=True,
        alias_generator=to_camel,
    )

@router.get(
    "/{file_key:path}",
    tags=["File"],
    summary="Получить изображение из шаблона",
    description="Возвращает изображение из шаблона по имени файла",
    responses={
        200: {
            "description": "Изображение из шаблона",
            "content": {
                "image/png": {
                    "schema": {
                        "type": "string",
                        "format": "binary"
                    }
                }
            }
        },
        404: {
            "description": "Файл не найден",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Файл не найден"
                    }
                }
            }
        }
    })
async def get_image(
        file_key: str,
        file_storage: HybridStorage = Depends(get_file_storage)
):
    image = file_storage.get(file_key)
    return Response(content=image, media_type="image/png")


@router.post(
    "/upload",
    tags=["File"],
    summary="Загрузить пользовательское изображение",
    description="Сохраняет изображение",
    response_class=HALResponse,
    responses={
        200: {
            "description": "Изображение сохранено",
            "content": {
                "application/json": {
                    "example": {
                        "key": "/key/to/file"
                    }
                }
            }
        },
        500: {
            "description": "Не получилось сохранить изображение",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Ошибка файловой системы"
                    }
                }
            }
        }
    })
async def save_image(
        file: UploadFile = File(...),
        file_storage: HybridStorage = Depends(get_file_storage)
):
    file_data = await file.read()
    extension = file.filename.split(".")[-1] if "." in file.filename else "png"

    file_key = file_storage.save(
        path=USER_IMAGE_PREFIX,
        file_data=file_data,
        extension=extension
    )

    return FileResponse(media_key=file_key)


@router.delete(
    "/{file_key:path}",
    tags=["File"],
    summary="Удалить изображение",
    description="Удаляет изображение по ключу файла",
    responses={
        200: {
            "description": "Изображение удалено"
        }
    })
async def delete_image(
        file_key: str,
        file_storage: HybridStorage = Depends(get_file_storage)
):
    file_storage.delete(file_key)
    return Response(status_code=200)