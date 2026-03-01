from fastapi import Request

from lti.services.request import FastAPIRequest


async def get_lti_request(request: Request) -> FastAPIRequest:
    lti_request = FastAPIRequest(request)
    await lti_request.parse_request()
    return lti_request