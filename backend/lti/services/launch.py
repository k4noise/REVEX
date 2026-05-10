import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional

from lti.exceptions import LtiLaunchException
from lti.models import LtiPlatform, LtiUser, LtiCourse
from lti.schemas import NrpsUser
from lti.services.nrps import NrpsService

logger = structlog.get_logger(__name__)


class LaunchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_launch(self, message_launch):
        launch_data = message_launch.get_launch_data()

        iss = launch_data.get("iss")
        if not iss:
            raise LtiLaunchException("Отсутствует 'iss' в LTI-launch")

        lti_user_id = launch_data.get("sub")
        if not lti_user_id:
            raise LtiLaunchException("Отсутствует 'sub' в LTI-launch")

        context = launch_data.get(
            "https://purl.imsglobal.org/spec/lti/claim/context",
            {},
        )
        lti_context_id = context.get("id")
        if not lti_context_id:
            raise LtiLaunchException("Отсутствует 'context.id' в LTI-launch")

        logger.info(
            "lti.launch.start",
            iss=iss,
            lti_user_id=lti_user_id,
            lti_context_id=lti_context_id,
        )

        res = await self.db.execute(select(LtiPlatform).filter_by(issuer=iss))
        platform = res.scalars().first()
        if not platform:
            platform = LtiPlatform(
                issuer=iss,
                guid=launch_data.get(
                    "https://purl.imsglobal.org/spec/lti/claim/tool_platform",
                    {},
                ).get("guid", "unknown"),
            )
            self.db.add(platform)
            await self.db.flush()
            logger.info(
                "lti.launch.platform_created",
                platform_id=platform.id,
                issuer=iss,
            )

        res = await self.db.execute(
            select(LtiUser).filter_by(platform_id=platform.id, lti_user_id=lti_user_id)
        )
        user = res.scalars().first()

        show_policy = False
        if not user:
            user = LtiUser(
                platform_id=platform.id,
                lti_user_id=lti_user_id,
                is_accept_policy=False,
            )
            self.db.add(user)
            await self.db.flush()
            show_policy = True
            logger.info(
                "lti.launch.user_created",
                user_id=user.id,
                platform_id=platform.id,
            )
        else:
            if not user.is_accept_policy:
                show_policy = True

        res = await self.db.execute(
            select(LtiCourse).filter_by(
                platform_id=platform.id,
                lti_context_id=lti_context_id,
            )
        )
        course = res.scalars().first()
        if not course:
            course = LtiCourse(
                platform_id=platform.id,
                lti_context_id=lti_context_id,
            )
            self.db.add(course)
            await self.db.flush()
            logger.info(
                "lti.launch.course_created",
                course_id=course.id,
                platform_id=platform.id,
                lti_context_id=lti_context_id,
            )

        logger.info(
            "lti.launch.ok",
            user_id=user.id,
            course_id=course.id,
            show_policy=show_policy,
        )

        return user.id, course.id, show_policy

    async def update_user_policy(self, user_id: int):
        res = await self.db.execute(
            select(LtiUser).filter_by(id=user_id)
        )
        user = res.scalars().first()

        if user:
            user.is_accept_policy = True
            logger.info(
                "lti.policy.accepted",
                user_id=user_id,
            )
            return user

        logger.warning(
            "lti.policy.user_not_found",
            user_id=user_id,
        )
        return None

    async def get_course_users_bind_map(
            self,
            message_launch,
            course_id: int,
    ) -> dict[str, NrpsUser]:
        res = await self.db.execute(
            select(LtiCourse.platform_id).where(LtiCourse.id == course_id)
        )
        platform_id = res.scalar_one_or_none()
        if not platform_id:
            logger.warning("lti.bind_map.course_not_found", course_id=course_id)
            return {}

        try:
            with NrpsService(message_launch) as nrps:
                stmt = select(LtiUser).where(
                    LtiUser.platform_id == platform_id,
                    )
                result = await self.db.execute(stmt)
                db_users = result.scalars().all()

                bind_map: dict[str, NrpsUser] = {}
                for db_user in db_users:
                    lti_id = db_user.lti_user_id
                    nrps_user = nrps.get_user_by_id(lti_id)
                    if nrps_user:
                        bind_map[str(db_user.id)] = nrps_user
                return bind_map

        except Exception as e:
            logger.error("lti.bind_map.nrps_error", course_id=course_id, error=str(e))
            return {}

    async def get_user_bind(
            self,
            internal_id: str,
    ) -> Optional[str]:
        res = await self.db.execute(
            select(LtiUser.lti_user_id).where(LtiUser.id == internal_id)
        )
        lti_id = res.scalar_one_or_none()
        return str(lti_id) if lti_id else None
