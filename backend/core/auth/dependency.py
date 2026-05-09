from collections.abc import Callable

from authx import TokenPayload
from fastapi import Depends, HTTPException
from starlette import status
from structlog.contextvars import bind_contextvars

from config.auth import auth
from core.auth.user_model import UserRole, User


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


async def get_user_base(
        payload: TokenPayload = Depends(auth.access_token_required),
) -> User:
    try:
        user = User(
            id=str(payload.sub),
            roles=payload.scopes or [],
            launch_id=str(getattr(payload, "launch_id", "")),
            course_id=str(getattr(payload, "course_id", "")),
            accepted_policy=_to_bool(getattr(payload, "accepted_policy", False)),
        )
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid role in token",
        )

    bind_contextvars(
        user_id=user.id,
        course_id=user.course_id,
        launch_id=user.launch_id,
    )

    return user


async def get_user(
        user: User = Depends(get_user_base),
) -> User:
    if not user.accepted_policy:
        raise HTTPException(
            status_code=status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS,
            detail="Policy not accepted",
        )
    return user


def get_user_with_any_role(*roles: UserRole) -> Callable:
    if not roles:
        raise ValueError("At least one role must be provided")

    async def require_any_of_roles(user: User = Depends(get_user)) -> User:
        if not any(role in roles for role in user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )
        return user

    return require_any_of_roles