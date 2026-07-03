from app.models.TimeslotDTO import TimeslotDTO
from helpers.module import discipline_acr
from helpers.timetable import row_to_day_time


_DCT_ALLOWED = {
    ("wednesday", "16:20", "17:50"),
    ("wednesday", "18:00", "19:30"),
    ("thursday", "16:20", "17:50"),
    ("thursday", "18:00", "19:30"),
}


def dct_allowed_row(module, row: int, days, timeslots: list[TimeslotDTO]) -> bool:
    """
    Checks whether a DCT module is allowed on the candidate row

    Args:
        module: Module being placed
        row: Candidate timetable row
        days: All timetable days
        timeslots: All timetable timeslots

    Returns:
        True if the candidate row is allowed for the module
    """
    if discipline_acr(module).strip().lower() != "dct":
        return True

    day_idx, slot_idx = row_to_day_time(row, timeslots)
    if day_idx >= len(days) or slot_idx >= len(timeslots):
        return False

    day = days[day_idx]
    slot = timeslots[slot_idx]

    day_name = str(getattr(day, "name", None) or day.get("name") or "").strip().lower()
    start = str(getattr(slot, "startHour", None) or slot.get("startHour") or "").strip()
    end = str(getattr(slot, "endHour", None) or slot.get("endHour") or "").strip()

    return (day_name, start, end) in _DCT_ALLOWED
