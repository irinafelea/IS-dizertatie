import uuid

from sqlalchemy import Column, Integer, Boolean, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID

from app.db import Base


class TimetableModule(Base):
    __tablename__ = "timetable_modules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    timetable_id = Column(UUID(as_uuid=True), nullable=False)

    module_id = Column(UUID(as_uuid=True), nullable=False)
    study_year_id = Column(UUID(as_uuid=True), nullable=False)
    room_id = Column(UUID(as_uuid=True), nullable=False)
    day_id = Column(UUID(as_uuid=True), nullable=False)
    hour_id = Column(UUID(as_uuid=True), nullable=False)

    row_index = Column(Integer, nullable=False)
    column_index = Column(Integer, nullable=False)
    number_of_columns = Column(Integer, nullable=False)

    even_week = Column(Boolean, nullable=False, server_default=text("false"))
    odd_week = Column(Boolean, nullable=False, server_default=text("false"))
    online = Column(Boolean, nullable=False, server_default=text("false"))

    show_discipline_title = Column(String, nullable=True)
    show_teacher = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
