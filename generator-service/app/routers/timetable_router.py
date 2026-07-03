from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.TimetableDTO import TimetableDTO
from app.services.timetable_service import (
    generate_timetable,
    get_rooms_timetable_by_version,
    get_study_year_timetable_by_version,
)

router = APIRouter(prefix="/timetables", tags=["timetables"])


@router.post("/generate/{semester_id}/{domain_id}/{enforce_bachelor_third_year_free_day}", response_model=TimetableDTO)
def generate_timetable_endpoint(
    semester_id: UUID,
    domain_id: UUID,
    enforce_bachelor_third_year_free_day: bool = False,
    seed: int | None = None,
    db: Session = Depends(get_db),
):
    """
    Generates a timetable for one semester and domain

    Args:
        semester_id: Semester id
        domain_id: Domain id
        enforce_bachelor_third_year_free_day: Enables the extra free-day rule
        seed: Optional random seed
        db: Database session

    Returns:
        Generated timetable DTO
    """
    return generate_timetable(
        db=db,
        semester_id=semester_id,
        domain_id=domain_id,
        enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
        seed=seed,
    )


@router.get("/rooms/{semester_id}/{domain_id}/{version}")
def get_rooms_timetable_endpoint(
    semester_id: UUID,
    domain_id: UUID,
    version: int,
    db: Session = Depends(get_db),
):
    """
    Returns the room timetable view for one saved version

    Args:
        semester_id: Semester id
        domain_id: Domain id
        version: Timetable version
        db: Database session

    Returns:
        Room timetable matrix
    """
    return get_rooms_timetable_by_version(
        db=db,
        semester_id=semester_id,
        domain_id=domain_id,
        version=version,
    )


@router.get("/study-years/{semester_id}/{domain_id}/{study_year_id}/{version}")
def get_study_year_timetable_endpoint(
    semester_id: UUID,
    domain_id: UUID,
    study_year_id: UUID,
    version: int,
    db: Session = Depends(get_db),
):
    """
    Returns the study-year timetable view for one saved version

    Args:
        semester_id: Semester id
        domain_id: Domain id
        study_year_id: Study-year id
        version: Timetable version
        db: Database session

    Returns:
        Study-year timetable matrix
    """
    return get_study_year_timetable_by_version(
        db=db,
        semester_id=semester_id,
        domain_id=domain_id,
        study_year_id=study_year_id,
        version=version,
    )
