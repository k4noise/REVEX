from pylti1p3.message_launch import MessageLaunch
from sqlalchemy import Sequence


from lti.schemas import UserRole
from lti.services.user import UserService


class JwtService:
    """
    Сервис подготовки данных для токенов JWT
    """

    def create_user_claims_at_jwt_object(self, raw_jwt: dict) -> dict:
        """
        Создает объект пользовательских данных на основе данных из другого jwt
        """
        return self._create_user_claims(
            raw_jwt.get("roles"),
            raw_jwt.get("launch_id"),
            raw_jwt.get("course_id"),
        )

    def create_user_claims_at_message_launch(self, message_launch: MessageLaunch, course_id: str) -> dict:
        """
        Создает объект пользовательских данных на основе данных из данных запуска LTI
        """
        roles = [role.value for role in UserService(message_launch).roles]
        launch_id = message_launch.get_launch_id()
        return self._create_user_claims(roles, launch_id, course_id)

    def _create_user_claims(self, roles: Sequence[UserRole], launch_id: str, course_id: str) -> dict:
        """
        Создает универсальный объект пользовательских данных
        """
        return {
            "roles": roles,
            "launch_id": launch_id,
            "course_id": course_id
        }
