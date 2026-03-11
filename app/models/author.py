import uuid
from sqlalchemy import Column, String, Text, BigInteger, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class Author(Base):
    __tablename__ = "authors"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    author = Column(Text, nullable=True)        # имя автора (поле называется "author", не "name")
    country = Column(Text, nullable=True)
    language = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    co_short = Column(Text, nullable=True)
    city = Column(Text, nullable=True)
    imitation = Column(Text, nullable=True)
    year = Column(String(50), nullable=True)
    face = Column(Text, nullable=True)
    target_audience = Column(Text, nullable=True)
    rhythms_style = Column(Text, nullable=True)
    exclude_words = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
