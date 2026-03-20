import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base

if TYPE_CHECKING:
    from template.models.template import Template


class TemplateElement(Base):
    __tablename__ = "template_elements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
    )

    parent_element_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("template_elements.id", ondelete="CASCADE"),
        nullable=True,
    )

    type: Mapped[str] = mapped_column(String(64), nullable=False)
    order: Mapped[int] = mapped_column(nullable=False)

    data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    display_mode: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    template: Mapped["Template"] = relationship(
        back_populates="elements",
    )

    parent: Mapped[Optional["TemplateElement"]] = relationship(
        "TemplateElement",
        remote_side="TemplateElement.id",
        back_populates="children",
    )

    children: Mapped[list["TemplateElement"]] = relationship(
        "TemplateElement",
        back_populates="parent",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="TemplateElement.order",
    )

    __table_args__ = (
        Index("idx_te_template_order", "template_id", "order"),
        Index("idx_te_template_parent_order", "template_id", "parent_element_id", "order"),
        Index("idx_te_template_type", "template_id", "type"),
    )