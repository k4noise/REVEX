import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException
from fastapi_hypermodel import HALResponse
from starlette import status
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from answer.dependencies import get_grade_service
from answer.schemas import UpdateAnswerDataRequest, UpdateAnswerScoresRequest
from answer.services.grade import GradeService
from core.auth.dependency import get_user, get_user_with_any_role
from core.auth.user_model import User, UserRole
from core.dependencies import get_cache
from core.rate_limiter import HintRateLimiter
from core.ttl_cache import RedisCache
from lti.dependencies import get_nrps_service
from lti.services.nrps import NrpsService
from report.dependencies import get_report_service, get_hint_context_service
from report.schemas.hint import NewHintRequest
from report.schemas.report_status import ReportStatus
from report.services.hint_context import HintContextService
from report.services.hint_generator import HintGenerator
from report.services.report import ReportService
from template.schemas.template import FullWorkResponse

router = APIRouter(prefix="/reports", tags=["Report"])


@router.get(
    "/{report_id}",
    tags=["Report"],
    response_class=HALResponse,
    response_model=FullWorkResponse,
    summary="Получить отчет",
    responses={
        401: {
            "description": "Неавторизованный доступ",
            "content": {"application/json": {"example": {"detail": "Не авторизован"}}},
        },
        404: {
            "description": "Доступ запрещен или шаблон не найден",
            "content": {
                "application/json": {
                    "example": {
                        "wrong_role": {
                            "description": "Доступ запрещен. Требуется роль студента",
                            "value": {"detail": "Не найдено"},
                        },
                        "wrong_course": {
                            "description": "Доступ запрещен. Шаблон другого курса",
                            "value": {"detail": "Не найдено"},
                        },
                        "not_a_author": {
                            "description": "Доступ запрещен. Студент - не автор шаблона",
                            "value": {"detail": "Не найдено"},
                        },
                        "not_for_instructor": {
                            "description": "Доступ запрещен. Отчет недоступен для преподавателя / ассистента",
                            "value": {"detail": "Не найдено"},
                        },
                        "no_report": {
                            "description": "Отчет не найден",
                            "value": {"detail": "Не найдено"},
                        },
                    }
                }
            },
        },
        500: {
            "description": "Ошибка БД",
            "content": {
                "application/json": {
                    "example": {
                        "bd_error": {
                            "summary": "Ошибка со стороны БД",
                            "value": {"detail": "Ошибка доступа к данным"},
                        },
                    }
                }
            },
        },
    },
)
async def get_report(
        request: Request,
        report_id: uuid.UUID,
        user: User = Depends(get_user),
        report_service: ReportService = Depends(get_report_service),
        nrps_service: NrpsService = Depends(get_nrps_service),
        hint_context: HintContextService = Depends(get_hint_context_service),
):
    report = await report_service.get(user, report_id, nrps_service)
    if report.status in {ReportStatus.CREATED, ReportStatus.SAVED}:
        cache: RedisCache = request.app.state.cache
        hint_context.cache(report, cache)
    return report


@router.patch(
    "/{report_id}",
    tags=["Report"],
    summary="Обновить ответы в отчете",
    responses={
        401: {
            "description": "Неавторизованный доступ",
            "content": {"application/json": {"example": {"detail": "Не авторизован"}}},
        },
        404: {
            "description": "Доступ запрещен или шаблон не найден",
            "content": {
                "application/json": {
                    "example": {
                        "wrong_role": {
                            "description": "Доступ запрещен. Требуется роль студента",
                            "value": {"detail": "Не найдено"},
                        },
                        "wrong_course": {
                            "description": "Доступ запрещен. Шаблон другого курса",
                            "value": {"detail": "Не найдено"},
                        },
                        "not_a_author": {
                            "description": "Доступ запрещен. Студент - не автор шаблона",
                            "value": {"detail": "Не найдено"},
                        },
                        "not_for_instructor": {
                            "description": "Доступ запрещен. Отчет недоступен для преподавателя / ассистента",
                            "value": {"detail": "Не найдено"},
                        },
                        "no_report": {
                            "description": "Отчет не найден",
                            "value": {"detail": "Не найдено"},
                        },
                    }
                }
            },
        },
        409: {
            "description": "Переход состояния отчета невозможен",
            "content": {
                "application/json": {
                    "example": {"detail": "Действие невозможно"},
                }
            },
        },
        500: {
            "description": "Ошибка со стороны БД",
            "content": {
                "application/json": {
                    "example": {"detail": "Ошибка доступа к данным"},
                }
            },
        },
    },
)
async def update_answers(
        report_id: uuid.UUID,
        answers: Sequence[UpdateAnswerDataRequest],
        user: User = Depends(get_user_with_any_role(UserRole.STUDENT)),
        report_service: ReportService = Depends(get_report_service),
):
    await report_service.save(user, report_id, answers)


@router.patch(
    "/{report_id}/grade",
    tags=["Report"],
    summary="Оценить отчет",
    responses={
        401: {
            "description": "Неавторизованный доступ",
            "content": {"application/json": {"example": {"detail": "Не авторизован"}}},
        },
        404: {
            "description": "Доступ запрещен или шаблон не найден",
            "content": {
                "application/json": {
                    "example": {
                        "wrong_role": {
                            "description": "Доступ запрещен. Требуется роль преподавателя / ассистента",
                            "value": {"detail": "Не найдено"},
                        },
                        "wrong_course": {
                            "description": "Доступ запрещен. Шаблон другого курса",
                            "value": {"detail": "Не найдено"},
                        },
                        "no_report": {
                            "description": "Отчет не найден",
                            "value": {"detail": "Не найдено"},
                        },
                    }
                }
            },
        },
        409: {
            "description": "Переход состояния отчета невозможен",
            "content": {
                "application/json": {
                    "example": {"detail": "Действие невозможно"},
                }
            },
        },
        500: {
            "description": "Служба AGS недоступна со стороны LMS или ошибка БД",
            "content": {
                "application/json": {
                    "examples": {
                        "lis_service_error": {
                            "summary": "Отсутствует доступ к службе оценок",
                            "value": {"detail": "Нет доступа к службе оценок"},
                        },
                        "bd_error": {
                            "summary": "Ошибка со стороны БД",
                            "value": {"detail": "Ошибка доступа к данным"},
                        },
                    }
                }
            },
        },
    },
)
async def save_grades(
        report_id: uuid.UUID,
        score_data: Sequence[UpdateAnswerScoresRequest],
        user: User = Depends(get_user_with_any_role(UserRole.TEACHER, UserRole.ASSISTANT)),
        grade_service: GradeService = Depends(get_grade_service),
):
    await grade_service.grade(user, report_id, score_data)


@router.post(
    "/{report_id}/submit",
    tags=["Report"],
    summary="Отправить отчет на проверку",
    responses={
        401: {
            "description": "Неавторизованный доступ",
            "content": {"application/json": {"example": {"detail": "Не авторизован"}}},
        },
        404: {
            "description": "Доступ запрещен или шаблон не найден",
            "content": {
                "application/json": {
                    "example": {
                        "wrong_role": {
                            "description": "Доступ запрещен. Требуется роль студента",
                            "value": {"detail": "Не найдено"},
                        },
                        "wrong_course": {
                            "description": "Доступ запрещен. Шаблон другого курса",
                            "value": {"detail": "Не найдено"},
                        },
                        "not_a_author": {
                            "description": "Доступ запрещен. Студент - не автор шаблона",
                            "value": {"detail": "Не найдено"},
                        },
                        "not_for_instructor": {
                            "description": "Доступ запрещен. Отчет недоступен для преподавателя / ассистента",
                            "value": {"detail": "Не найдено"},
                        },
                        "no_report": {
                            "description": "Отчет не найден",
                            "value": {"detail": "Не найдено"},
                        },
                    }
                }
            },
        },
        409: {
            "description": "Переход состояния отчета невозможен",
            "content": {
                "application/json": {
                    "example": {"detail": "Действие невозможно"},
                }
            },
        },
        500: {
            "description": "Ошибка со стороны БД",
            "content": {
                "application/json": {
                    "example": {"detail": "Ошибка доступа к данным"},
                }
            },
        },
    },
)
async def send_to_grade(
        report_id: uuid.UUID,
        user: User = Depends(get_user_with_any_role(UserRole.STUDENT)),
        grade_service: GradeService = Depends(get_grade_service),
):
    await grade_service.send_to_grade(user, report_id)


@router.delete(
    "/{report_id}/submit",
    tags=["Report"],
    summary="Убрать отчет с проверки",
    responses={
        401: {
            "description": "Неавторизованный доступ",
            "content": {"application/json": {"example": {"detail": "Не авторизован"}}},
        },
        404: {
            "description": "Доступ запрещен или шаблон не найден",
            "content": {
                "application/json": {
                    "example": {
                        "wrong_role": {
                            "description": "Доступ запрещен. Требуется роль студента",
                            "value": {"detail": "Не найдено"},
                        },
                        "wrong_course": {
                            "description": "Доступ запрещен. Шаблон другого курса",
                            "value": {"detail": "Не найдено"},
                        },
                        "not_a_author": {
                            "description": "Доступ запрещен. Студент - не автор шаблона",
                            "value": {"detail": "Не найдено"},
                        },
                        "no_report": {
                            "description": "Отчет не найден",
                            "value": {"detail": "Не найдено"},
                        },
                    }
                }
            },
        },
        500: {
            "description": "Ошибка со стороны БД",
            "content": {
                "application/json": {
                    "example": {"detail": "Ошибка доступа к данным"},
                }
            },
        },
    },
)
async def cancel_send_to_grade(
        report_id: uuid.UUID,
        user: User = Depends(get_user_with_any_role(UserRole.STUDENT)),
        report_service: ReportService = Depends(get_report_service),
):
    await report_service.unsubmit(user, report_id)


@router.post(
    "/{report_id}/hint",
    tags=["Report"],
    summary="Получить подсказку при заполнении отчета",
    responses={
        401: {
            "description": "Неавторизованный доступ",
            "content": {"application/json": {"example": {"detail": "Не авторизован"}}},
        },
        404: {
            "description": "Доступ запрещен или шаблон не найден",
            "content": {
                "application/json": {
                    "example": {
                        "description": "Доступ запрещен. Студент - не автор шаблона",
                        "value": {"detail": "Не найдено"},
                    }
                }
            },
        },
        429: {
            "description": "Превышен лимит запросов на подсказки",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Слишком много запросов на подсказку. Повторите позже."
                    }
                }
            },
        },
    },
)
async def get_hint(
        report_id: uuid.UUID,
        hint_request: NewHintRequest,
        user: User = Depends(get_user_with_any_role(UserRole.STUDENT)),
        cache: RedisCache = Depends(get_cache),
        report_service: ReportService = Depends(get_report_service),
        hint_context: HintContextService = Depends(get_hint_context_service),
):
    limiter = HintRateLimiter(
        cache,
        free_attempts=2,
        max_attempts=5,
        base_delay_seconds=30,
        multiplier=4.0,
        max_delay_seconds=3600,
        state_ttl_seconds=86400,
    )

    decision = limiter.check_and_consume(
        user_id=str(user.id),
        report_id=report_id,
        element_id=hint_request.current.element_id,
        answer_payload=hint_request.current.data,
    )

    if not decision.allowed:
        headers = {}
        if decision.retry_after > 0:
            headers["Retry-After"] = str(decision.retry_after)

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много запросов на подсказку. Повторите позже.",
            headers=headers,
        )

    context = hint_context.get_from_cache(hint_request, user, report_id, cache)
    if context is None:
        report = await report_service.get(user, report_id, None)
        hint_context.cache(report, cache)
        context = hint_context.get_from_cache(hint_request, user, report_id, cache)

    if context is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    generator = HintGenerator()
    hint = await generator.generate(context)

    if hint is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return JSONResponse({"hint": hint})