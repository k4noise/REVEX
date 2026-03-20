import os

from fastapi import APIRouter, Query, Depends, status
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pylti1p3.oidc_login import OIDCException

from config.auth import auth
from core.auth.depedency import get_user_base
from core.db import get_session
from core.auth.user_model import User
from lti.depedencies import get_lti_request, get_lti_cache_storage
from lti.services.jwt import JwtService
from lti.services.launch import LaunchService
from lti.services.message_launch import FastAPIMessageLaunch
from lti.services.oidc_login import FastAPIOIDCLogin
from lti.services.request import FastAPIRequest

router = APIRouter(prefix="/lti", tags=["LTI"])


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
        return JSONResponse({"detail": 'Отсутствует параметр "target_link_uri"'}, status.HTTP_400_BAD_REQUEST)

    oidc_login = FastAPIOIDCLogin(
        lti_request, lti_request.get_tool(), launch_data_storage=cache_storage
    )
    try:
        return oidc_login.disable_check_cookies().redirect(target_link_uri)
    except OIDCException:
        return JSONResponse({"detail": 'Вход не выполнен, попробуйте ещё раз'}, status.HTTP_400_BAD_REQUEST)


@router.post("/launch", status_code=302)
async def launch(
        lti_request: FastAPIRequest = Depends(get_lti_request),
        session: AsyncSession = Depends(get_session),
        cache_storage=Depends(get_lti_cache_storage),
):
    message_launch = FastAPIMessageLaunch(
        lti_request, lti_request.get_tool(), launch_data_storage=cache_storage
    )
    message_launch.validate_registration()

    launch_service = LaunchService(session)
    user_id, course_id, show_policy = await launch_service.process_launch(message_launch)

    access_token, refresh_token = JwtService().create_tokens_for_launch(user_id, message_launch, course_id, show_policy)
    base_url = os.getenv("FRONTEND_URL", "")
    response = RedirectResponse(url=base_url, status_code=status.HTTP_302_FOUND)

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
        return JSONResponse({"detail": "User not found"}, status.HTTP_404_NOT_FOUND)

    response = JSONResponse({"status": "ok"})
    access_token, refresh_token = JwtService().create_tokens_for_user(current_user, accepted_policy=True)
    auth.set_access_cookies(access_token, response=response)
    auth.set_refresh_cookies(refresh_token, response=response)
    return response


@router.get("/jwks")
async def jwks(lti_request: FastAPIRequest = Depends(get_lti_request)):
    return JSONResponse(lti_request.get_tool().get_jwks())

