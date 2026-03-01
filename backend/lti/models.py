from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.schema import UniqueConstraint

from core.db import Base


class LtiPlatform(Base):
    __tablename__ = "lti_platforms"
    id = Column(Integer, primary_key=True)
    guid = Column(String(255), unique=True, nullable=False)
    issuer = Column(String(512), nullable=False)


class LtiCourse(Base):
    __tablename__ = "lti_courses"
    id = Column(Integer, primary_key=True)
    platform_id = Column(Integer, ForeignKey("lti_platforms.id"), nullable=False)
    lti_context_id = Column(String(255), nullable=False)
    __table_args__ = (UniqueConstraint("platform_id", "lti_context_id"),)


class LtiUser(Base):
    __tablename__ = "lti_users"
    id = Column(Integer, primary_key=True)
    platform_id = Column(Integer, ForeignKey("lti_platforms.id"), nullable=False)
    lti_user_id = Column(String(255), nullable=False)
    is_accept_policy = Column(Boolean, default=False, nullable=False)
    __table_args__ = (UniqueConstraint("platform_id", "lti_user_id"),)