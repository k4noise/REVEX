import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    Float,
    TIMESTAMP,
    ForeignKey,
    Index,
    text,
    FetchedValue,
    desc,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from core.db import Base
from report.schemas.report_status import ReportStatusType


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("templates.id"), nullable=False
    )
    author_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        ReportStatusType, nullable=False
    )
    grader_id: Mapped[str | None] = mapped_column(String, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=FetchedValue(),
    )

    answers: Mapped[list["Answer"]] = relationship(
        "Answer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    template: Mapped["Template"] = relationship(
        "Template",
        back_populates="reports",
        lazy="noload",
    )

    __table_args__ = (
        Index(
            "reports_template_id_created_idx",
            "template_id",
            desc(created_at),
        ),
        Index(
            "reports_author_id_template_id_created_at_idx",
            "author_id",
            "template_id",
            "created_at",
        ),
    )