from pylti1p3.message_launch import MessageLaunch


class CourseService:
    def __init__(self, message_launch: MessageLaunch):
        self.message_launch = message_launch
        self.course_data = message_launch \
            .get_launch_data() \
            .get("https://purl.imsglobal.org/spec/lti/claim/context")

    @property
    def name(self) -> str:
        return self.course_data.get("title")

    @property
    def id(self) -> str:
        return self.course_data.get("id")
