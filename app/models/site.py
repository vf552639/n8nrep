import uuid

from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Site(Base):
    __tablename__ = "sites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    domain = Column(String(200), nullable=False)
    country = Column(String(10), nullable=False)
    language = Column(String(10), nullable=False)
    is_active = Column(Boolean, default=True)
    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    legal_info = Column(JSONB, nullable=True)

    template = relationship("Template", back_populates="sites")
