import uuid

import sqlalchemy as sa

from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database import Base


class Site(Base):
    __tablename__ = "sites"

    id = Column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    domain = Column(String(200), nullable=False)
    country = Column(String(10), nullable=False)
    language = Column(String(10), nullable=False)
    is_active = Column(Boolean, default=True)
    template_id = Column(
        sa.Uuid(as_uuid=True),
        ForeignKey("templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    legal_info = Column(sa.JSON, nullable=True)

    template = relationship("Template", back_populates="sites")
