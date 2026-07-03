import uuid

from sqlalchemy import Column, Integer, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from app.db import Base


class Timetable(Base):
    __tablename__ = "timetables"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    semester_id = Column(UUID(as_uuid=True), nullable=False)
    domain_id = Column(UUID(as_uuid=True), nullable=False)

    version = Column(Integer, nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))