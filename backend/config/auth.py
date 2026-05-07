import os
from datetime import timedelta

from authx import AuthXConfig, AuthX

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY is not set")

config = AuthXConfig(
    JWT_SECRET_KEY=JWT_SECRET_KEY,
    JWT_TOKEN_LOCATION=["cookies"],
    JWT_COOKIE_HTTP_ONLY=True,

    JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15),
    JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=1),

    JWT_COOKIE_CSRF_PROTECT=False,
    JWT_COOKIE_SECURE=False,
)

auth = AuthX(config=config)