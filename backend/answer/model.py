import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import JSON, Float, ForeignKey, Uuid, CheckConstraint, Text
from sqlalchemy.orm import mapped_column, Mapped, relationship

from core.db import Base

if TYPE_CHECKING:
    from report.model import Report
    from template.models.template_element import TemplateElement


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        index=True,
    )

    element_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("template_elements.id", ondelete="CASCADE"),
        index=True,
    )

    data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    pre_grade: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    report: Mapped["Report"] = relationship("Report", back_populates="answers")
    element: Mapped["TemplateElement"] = relationship("TemplateElement")

    __table_args__ = (
        CheckConstraint("score >= 0.0 AND score <= 1.0", name="ck_reports_score_range"),
    )