from pylti1p3.message_launch import MessageLaunch

from config.auth import auth
from core.user_model import  User
from lti.services.user import UserService


class JwtService:

    def _create_claims(self, roles: list[str], launch_id: str, course_id: str, accepted_policy: bool) -> dict:
        return {
            "scopes": roles,
            "launch_id": launch_id,
            "course_id": course_id,
            "accepted_policy": accepted_policy,
        }

    def _create_tokens(self, uid: str, claims: dict) -> tuple[str, str]:
        scopes = claims.pop("scopes", [])
        access_token = auth.create_access_token(uid=uid, scopes=scopes, data=claims)
        refresh_token = auth.create_refresh_token(uid=uid, scopes=scopes, data=claims)
        return access_token, refresh_token

    def create_tokens_for_user(self, user: User, accepted_policy: bool | None = None) -> tuple[str, str]:
        claims = self._create_claims(
            roles=[role.value for role in user.roles],
            launch_id=user.launch_id,
            course_id=user.course_id,
            accepted_policy=accepted_policy if accepted_policy is not None else user.accepted_policy,
        )
        return self._create_tokens(uid=user.id, claims=claims)

    def create_tokens_for_launch(self, user_id: int, message_launch: MessageLaunch, course_id: str, show_policy: bool) -> tuple[str, str]:
        claims = self._create_claims(
            roles=[role.value for role in UserService(message_launch).roles],
            launch_id=message_launch.get_launch_id(),
            course_id=course_id,
            accepted_policy=not show_policy,
        )
        return self._create_tokens(uid=str(user_id), claims=claims)