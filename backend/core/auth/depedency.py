from authx import TokenPayload
from fastapi import Depends, HTTPException
from starlette import status

from config.auth import auth
from core.auth.user_model import UserRole, User


async def get_user_base(
        payload: TokenPayload = Depends(auth.access_token_required),
) -> User:
    accepted_policy = getattr(payload, "accepted_policy", False)

    try:
        roles = [UserRole(r) for r in (payload.scopes or [])]
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid role in token")

    return User(
        id=str(payload.sub),
        roles=roles,
        launch_id=str(getattr(payload, "launch_id", "")), # Тоже лучше через getattr на всякий случай
        course_id=str(getattr(payload, "course_id", "")),
        accepted_policy=accepted_policy,
    )


async def get_user(
        user: User = Depends(get_user_base),
) -> User:
    if not user.accepted_policy:
        raise HTTPException(status_code=status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS, detail="Policy not accepted")
    return user

def get_user_with_any_role(*roles: UserRole):
    """Возвращает данные пользователя, если он имеет хотя бы одну необходимую роль"""

    async def require_any_of_roles(user: User = Depends(get_user)) -> User:
        if not any(role in roles for role in user.roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return require_any_of_roles