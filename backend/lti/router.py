import os
import uuid
from authx import TokenPayload
from fastapi import APIRouter, Depends, Form, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pylti1p3.oidc_login import OIDCException
from sqlalchemy.ext.asyncio import AsyncSession

from config.auth import auth
from core.auth.dependency import get_user_base
from core.auth.user_model import User, UserRole
from core.db import get_session
from lti.dependencies import get_lti_request, get_lti_cache_storage
from lti.exceptions import (
    LtiLaunchException,
    LtiLoginException,
    LtiTokenRefreshException,
    LtiUserNotFoundException,
)
from lti.services.deep_link import DeepLinkService
from lti.services.jwt import JwtService
from lti.services.launch import LaunchService
from lti.services.message_launch import FastAPIMessageLaunch
from lti.services.oidc_login import FastAPIOIDCLogin
from lti.services.lti_request import FastAPIRequest

router = APIRouter(prefix="/lti", tags=["LTI"])
templates = Jinja2Templates(directory="lti")

def _is_deep_link_launch(message_launch: FastAPIMessageLaunch) -> bool:
    if hasattr(message_launch, "is_deep_link_launch"):
        return message_launch.is_deep_link_launch()
    if hasattr(message_launch, "is_deep_linking_launch"):
        return message_launch.is_deep_linking_launch()
    return False

@router.post("/deep-link", response_class=HTMLResponse)
async def deep_link_launch(
        request: Request,
        lti_request: FastAPIRequest = Depends(get_lti_request),
        cache_storage=Depends(get_lti_cache_storage),
        session: AsyncSession = Depends(get_session),
):
    try:
        message_launch = FastAPIMessageLaunch(
            lti_request,
            lti_request.get_tool(),
            launch_data_storage=cache_storage,
        )
        message_launch.get_launch_data()
    except Exception as e:
        raise LtiLaunchException(f"Ошибка deep-link launch: {e}") from e

    if not _is_deep_link_launch(message_launch):
        raise LtiLaunchException("Это не deep linking launch")

    launch_service = LaunchService(session)
    _, internal_course_id, _ = await launch_service.process_launch(message_launch)

    deep_link_service = DeepLinkService(session)
    state = await deep_link_service.save_state(message_launch)
    templates_list = await deep_link_service.get_templates_for_picker(course_id=internal_course_id)

    launch_data = message_launch.get_launch_data()
    settings = launch_data.get(
        "https://purl.imsglobal.org/spec/lti-dl/claim/deep_linking_settings",
        {},
    )

    return templates.TemplateResponse(
        request=request,
        name="picker.html",
        context={
            "state": state,
            "title": settings.get("title") or "Выберите шаблон",
            "text": settings.get("text") or "",
            "accept_multiple": False,
            "templates": templates_list,
        },
    )

@router.post("/deep-link/select", response_class=HTMLResponse, name="lti_deep_link_select")
async def deep_link_select(
        request: Request,
        session: AsyncSession = Depends(get_session),
):
    form = await request.form()
    state = str(form.get("state", "")).strip()
    raw_template_ids = form.getlist("template_ids")

    if not state:
        raise LtiLaunchException("Не передан state")
    if not raw_template_ids:
        raise LtiLaunchException("Не выбран шаблон")

    try:
        template_ids = [uuid.UUID(str(raw_template_ids[0]).strip())]
    except (ValueError, IndexError) as e:
        raise LtiLaunchException("Некорректный template_id") from e

    deep_link_service = DeepLinkService(session)
    html = await deep_link_service.create_response_html(
        state=state,
        template_ids=template_ids,
    )
    return HTMLResponse(content=html)

@router.post("/deep-link/cancel", response_class=HTMLResponse, name="lti_deep_link_cancel")
async def deep_link_cancel(
        state: str = Form(...),
        session: AsyncSession = Depends(get_session),
):
    deep_link_service = DeepLinkService(session)
    html = await deep_link_service.create_response_html(
        state=state,
        template_ids=[],
    )
    return HTMLResponse(content=html)

@router.get("/login")
@router.post("/login")
async def login(
        lti_request: FastAPIRequest = Depends(get_lti_request),
        target_link_uri: str | None = Query(None),
        cache_storage=Depends(get_lti_cache_storage),
):
    if not target_link_uri:
        target_link_uri = lti_request.get_param("target_link_uri")
    if not target_link_uri:
        raise LtiLoginException('Отсутствует параметр "target_link_uri"')
    oidc_login = FastAPIOIDCLogin(
        lti_request,
        lti_request.get_tool(),
        launch_data_storage=cache_storage,
    )
    try:
        return oidc_login.disable_check_cookies().redirect(target_link_uri)
    except OIDCException as e:
        raise LtiLoginException("Вход не выполнен, попробуйте ещё раз") from e

@router.post("/launch", status_code=302)
async def launch(
        lti_request: FastAPIRequest = Depends(get_lti_request),
        session: AsyncSession = Depends(get_session),
        cache_storage=Depends(get_lti_cache_storage),
):
    try:
        message_launch = FastAPIMessageLaunch(
            lti_request,
            lti_request.get_tool(),
            launch_data_storage=cache_storage,
        )
        launch_data = message_launch.get_launch_data()
    except Exception as e:
        raise LtiLaunchException(f"Ошибка валидации LTI launch: {e}") from e

    launch_service = LaunchService(session)
    user_id, course_id, show_policy = await launch_service.process_launch(message_launch)
    access_token, refresh_token = JwtService().create_tokens_for_launch(
        user_id, message_launch, str(course_id), show_policy,
    )

    frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
    custom = launch_data.get("https://purl.imsglobal.org/spec/lti/claim/custom", {}) or {}
    template_id = str(custom.get("template_id", "")).strip()

    if frontend_url:
        redirect_url = f"{frontend_url}/template/{template_id}/reports" if template_id else frontend_url
    else:
        redirect_url = f"/template/{template_id}/reports" if template_id else "/"

    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    auth.set_access_cookies(access_token, response=response)
    auth.set_refresh_cookies(refresh_token, response=response)
    return response

@router.post("/accept-policy")
async def accept_policy(
        session: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_user_base),
):
    launch_service = LaunchService(session)
    updated = await launch_service.update_user_policy(int(current_user.id))
    if not updated:
        raise LtiUserNotFoundException(int(current_user.id))
    response = JSONResponse({"status": "ok"})
    access_token, refresh_token = JwtService().create_tokens_for_user(current_user, accepted_policy=True)
    auth.set_access_cookies(access_token, response=response)
    auth.set_refresh_cookies(refresh_token, response=response)
    return response

@router.post("/jwt-refresh")
async def refresh_tokens(payload: TokenPayload = Depends(auth.refresh_token_required)):
    try:
        user_id = str(payload.sub)
        roles = [UserRole(r) for r in getattr(payload, "scopes", [])]
        launch_id = str(getattr(payload, "launch_id", ""))
        course_id = str(getattr(payload, "course_id", ""))
        accepted_policy = getattr(payload, "accepted_policy", False)
    except Exception as e:
        raise LtiTokenRefreshException(f"Некорректный payload refresh-токена: {e}") from e

    current_user = User(id=user_id, roles=roles, launch_id=launch_id, course_id=course_id, accepted_policy=accepted_policy)
    access_token, new_refresh_token = JwtService().create_tokens_for_user(user=current_user, accepted_policy=accepted_policy)
    response = JSONResponse({"status": "ok", "detail": "Tokens refreshed"})
    auth.set_access_cookies(access_token, response=response)
    auth.set_refresh_cookies(new_refresh_token, response=response)
    return response

@router.get("/jwks")
async def jwks(lti_request: FastAPIRequest = Depends(get_lti_request)):
    return JSONResponse(lti_request.get_tool().get_jwks())