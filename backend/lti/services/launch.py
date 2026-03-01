from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from lti.models import LtiPlatform, LtiUser, LtiCourse


class LaunchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_launch(self, message_launch):
        launch_data = message_launch.get_launch_data()

        iss = launch_data.get('iss')

        res = await self.db.execute(select(LtiPlatform).filter_by(issuer=iss))
        platform = res.scalars().first()
        if not platform:
            platform = LtiPlatform(issuer=iss, guid=launch_data.get('https://purl.imsglobal.org/spec/lti/claim/tool_platform', {}).get('guid', 'unknown'))
            self.db.add(platform)
            await self.db.flush()

        lti_user_id = launch_data.get('sub')
        res = await self.db.execute(
            select(LtiUser).filter_by(platform_id=platform.id, lti_user_id=lti_user_id)
        )
        user = res.scalars().first()

        show_policy = False
        if not user:
            user = LtiUser(platform_id=platform.id, lti_user_id=lti_user_id, is_accept_policy=True)
            self.db.add(user)
            show_policy = True
        else:
            if not user.is_accept_policy:
                show_policy = True
            user.is_accept_policy = True

        context = launch_data.get('https://purl.imsglobal.org/spec/lti/claim/context', {})
        lti_context_id = context.get('id')

        res = await self.db.execute(
            select(LtiCourse).filter_by(platform_id=platform.id, lti_context_id=lti_context_id)
        )
        course = res.scalars().first()
        if not course:
            course = LtiCourse(platform_id=platform.id, lti_context_id=lti_context_id)
            self.db.add(course)

        await self.db.commit()
        return user.id, course.id, show_policy