from typing import Dict, List, Any, Tuple

from app.models.DayDTO import DayDTO
from app.models.RoomDTO import RoomDTO
from app.models.TimeslotDTO import TimeslotDTO

COLOR_EMPTY = "#ffffff"
COLOR_BLOCKED = "#be0c0c"

SY_COLOR = {
    "IR1": "#6aabda",
    "IR2": "#4686da",
    "IR3": "#2f62a0",
    "IE1": "#a09d6a",
    "IE2": "#dedb26",
    "IE3": "#aaaa7f",
    "AI1": "#8fd952",
    "AI2": "#559e36",
    "AI3": "#27d21a",
    "IS1": "#ab74e9",
    "IS2": "#7c48b7",
    "BIOINFO1": "#a16eda",
    "BIOINFO2": "#8653c0",
    "CS1": "#633994",
    "AIDC1": "#592e8a",
    "ISR1": "#7545ac",
    "BD1": "#7944b6",
}


def _id_str(value: Any) -> str:
    """
    Converts an optional value to a string id

    Args:
        value: Source value

    Returns:
        String value or an empty string
    """
    return str(value) if value is not None else ""


def _primary_sy(value: str) -> str:
    """
    Extracts the primary study-year label from a combined label

    Args:
        value: Raw study-year label

    Returns:
        Primary study-year label
    """
    if not value:
        return ""
    value = value.strip()
    if "/" in value:
        value = value.split("/", 1)[0].strip()
    if "+" in value:
        value = value.split("+", 1)[0].strip()
    return value


def _extract_sy_from_text(cell_text: str) -> str:
    """
    Extracts the first study-year label from rendered room text

    Args:
        cell_text: Rendered cell text

    Returns:
        Extracted study-year label
    """
    if not cell_text:
        return ""

    parts = [p.strip() for p in cell_text.split("/")]

    def extract(part: str) -> str:
        """
        Extracts the study-year suffix from one side of the cell text

        Args:
            part: One side of the rendered cell text

        Returns:
            Extracted study-year label
        """
        if " - " not in part:
            return ""
        return part.split(" - ", 1)[1].strip()

    left_sy = extract(parts[0])
    if left_sy:
        return left_sy

    if len(parts) > 1:
        right_sy = extract(parts[1])
        if right_sy:
            return right_sy

    return ""


def _color_for_text(cell_text: str) -> str:
    """
    Resolves the room-cell color from rendered text

    Args:
        cell_text: Rendered cell text

    Returns:
        Cell background color
    """
    sy = _extract_sy_from_text(cell_text)
    key = _primary_sy(sy)
    return SY_COLOR.get(key, COLOR_EMPTY)


def _merge_side_text(odd_txt: str, even_txt: str) -> str:
    """
    Merges odd-week and even-week text into one room cell label

    Args:
        odd_txt: Odd-week text
        even_txt: Even-week text

    Returns:
        Merged room cell text
    """
    odd_txt = (odd_txt or "").strip()
    even_txt = (even_txt or "").strip()

    if odd_txt and even_txt:
        if odd_txt == even_txt:
            return odd_txt
        return f"{odd_txt} / {even_txt}"

    if odd_txt and not even_txt:
        return f"{odd_txt} / *"

    if even_txt and not odd_txt:
        return f"* / {even_txt}"

    return ""


def _split_study_years(value: str) -> list[str]:
    """
    Splits a combined study-year label string

    Args:
        value: Combined study-year label

    Returns:
        Individual study-year labels
    """
    return [part.strip() for part in str(value or "").split("+") if part.strip()]


def _add_bucket(
    bucket: Dict[Tuple[str, str, int], Dict[str, set[str]]],
    key: Tuple[str, str, int],
    base: str,
    study_year: str,
):
    """
    Adds a rendered entry into a room-cell bucket

    Args:
        bucket: Target bucket map
        key: Bucket key
        base: Teacher or discipline label
        study_year: Study-year label

    Returns:
        None
    """
    if not base and not study_year:
        return

    bucket.setdefault(key, {})
    bucket[key].setdefault(base, set())
    for part in _split_study_years(study_year):
        bucket[key][base].add(part)


def _render_side(entries: Dict[str, set[str]]) -> str:
    """
    Renders one parity side of a room cell

    Args:
        entries: Base labels mapped to study-year labels

    Returns:
        Rendered side text
    """
    parts: list[str] = []

    for base in sorted(entries):
        study_years = sorted(entries[base])
        joined_sy = " + ".join(study_years).strip()

        if base and joined_sy:
            parts.append(f"{base} - {joined_sy}")
        elif base:
            parts.append(base)
        elif joined_sy:
            parts.append(joined_sy)

    return " + ".join(parts).strip()


def _room_code(room: RoomDTO) -> str:
    """
    Extracts the short display code of a room

    Args:
        room: Source room

    Returns:
        Short room code
    """
    official_name = str(room.officialName or "").strip()
    if not official_name:
        return _id_str(room.id)

    parts = official_name.split("-")
    return parts[-1].strip() if parts else official_name


def build_rooms_timetable_matrix(
    items: List[Dict[str, Any]],
    days: List[DayDTO],
    timeslots: List[TimeslotDTO],
    rooms: List[RoomDTO],
) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
    """
    Builds the room timetable matrix from saved timetable items

    Args:
        items: Saved timetable items
        days: Generation days
        timeslots: Generation timeslots
        rooms: Available rooms

    Returns:
        Room timetable matrix by day and hour
    """

    day_ids = [_id_str(d.get("id")) for d in days if d.get("id") is not None]
    hour_ids = [_id_str(t.get("id")) for t in timeslots if t.get("id") is not None]

    rooms_sorted = sorted(
        [r for r in rooms if r.get("id") is not None],
        key=lambda r: (r.get("officialName") or "")
    )

    room_ids = [_id_str(r.get("id")) for r in rooms_sorted]
    room_index = {rid: idx for idx, rid in enumerate(room_ids)}
    room_count = len(room_ids)

    common: Dict[Tuple[str, str, int], Dict[str, set[str]]] = {}
    odd: Dict[Tuple[str, str, int], Dict[str, set[str]]] = {}
    even: Dict[Tuple[str, str, int], Dict[str, set[str]]] = {}
    blocked: set[Tuple[str, str, int]] = set()

    for item in items:
        day = _id_str(item.get("dayId"))
        hour = _id_str(item.get("hourId"))
        room_id = _id_str(item.get("roomId"))

        if not day or not hour or not room_id:
            continue

        if room_id not in room_index:
            continue

        room_pos = room_index[room_id]
        key = (day, hour, room_pos)

        teacher = str(item.get("showTeacher") or "").strip()
        discipline = str(item.get("showDisciplineTitle") or "").strip()

        if teacher.lower() == "blocked":
            blocked.add(key)
            continue

        study_year = str(item.get("studyYearLabel") or "").strip()
        base = teacher or discipline

        even_week = bool(item.get("evenWeek", False))
        odd_week = bool(item.get("oddWeek", False))

        if even_week and odd_week:
            _add_bucket(common, key, base, study_year)
        elif odd_week:
            _add_bucket(odd, key, base, study_year)
        elif even_week:
            _add_bucket(even, key, base, study_year)

    out: Dict[str, Dict[str, List[Dict[str, str]]]] = {}

    for day_id in day_ids:
        out[day_id] = {}
        for hour_id in hour_ids:
            cells = [{"text": "", "color": COLOR_EMPTY} for _ in range(room_count)]

            for room_pos in range(room_count):
                key = (day_id, hour_id, room_pos)

                if key in blocked:
                    cells[room_pos] = {"text": "blocked", "color": COLOR_BLOCKED}
                    continue

                common_entries = common.get(key, {})
                odd_entries = odd.get(key, {})
                even_entries = even.get(key, {})

                if not common_entries and not odd_entries and not even_entries:
                    cells[room_pos] = {"text": "", "color": COLOR_EMPTY}
                    continue

                odd_side_entries: Dict[str, set[str]] = {}
                even_side_entries: Dict[str, set[str]] = {}

                for source in (common_entries, odd_entries):
                    for base, study_years in source.items():
                        odd_side_entries.setdefault(base, set()).update(study_years)

                for source in (common_entries, even_entries):
                    for base, study_years in source.items():
                        even_side_entries.setdefault(base, set()).update(study_years)

                odd_side = _render_side(odd_side_entries)
                even_side = _render_side(even_side_entries)
                cell_text = _merge_side_text(odd_side, even_side).strip()

                if cell_text:
                    cells[room_pos] = {
                        "text": cell_text,
                        "color": _color_for_text(cell_text),
                    }
                else:
                    cells[room_pos] = {"text": "-", "color": COLOR_EMPTY}

            out[day_id][hour_id] = cells

    return out
