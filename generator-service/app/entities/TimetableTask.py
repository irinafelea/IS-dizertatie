import uuid

from sqlalchemy import Column, String, Integer, Boolean, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db import Base


class TimetableTask(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    module_ids = Column(JSONB, nullable=False)
    domain_id = Column(UUID(as_uuid=True), nullable=False)
    semester_id = Column(UUID(as_uuid=True), nullable=False)

    category = Column(String(32), nullable=False)
    duration_hours = Column(Integer, nullable=False)
    number_of_modules = Column(Integer, nullable=False, server_default=text("1"))

    common = Column(Boolean, nullable=False, server_default=text("false"))

    optional = Column(Boolean, nullable=False, server_default=text("false"))
    pack = Column(Integer, nullable=True)

    group_index = Column(Integer, nullable=True)
    group_span = Column(Integer, nullable=True)

    number_of_students = Column(Integer, nullable=False)
    number_of_groups = Column(Integer, nullable=False)

    study_years_ids = Column(JSONB, nullable=False)
    study_years_labels = Column(String(500), nullable=False)
    module_targets = Column(JSONB, nullable=True)

    pair_group_key = Column(String(500), nullable=True)

    online = Column(Boolean, nullable=False, server_default=text("false"))

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
