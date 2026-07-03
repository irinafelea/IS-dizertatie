import uuid
from typing import Dict, List, Any

from app.models.DayDTO import DayDTO
from app.models.TimeslotDTO import TimeslotDTO
from app.models.ModuleDTO import ModuleDTO
from app.models.RoomDTO import RoomDTO
from helpers._dget import _dget


def _id_str(value) -> str | None:
    """
    Converts an optional value to a string id

    Args:
        value: Source value

    Returns:
        String value or None
    """
    return str(value) if value is not None else None


def _to_plain(value):
    """
    Converts model values into plain Python data

    Args:
        value: Source value

    Returns:
        Plain value representation
    """
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    return value


def _split_sy_labels(value: str) -> List[str]:
    """
    Splits a combined study-year label string

    Args:
        value: Combined study-year label

    Returns:
        Individual study-year labels
    """
    return [part.strip() for part in str(value or "").split("+") if part.strip()]


def _match_study_year_entry(item: Dict[str, Any], study_year_label: str) -> dict | None:
    """
    Finds the study-year entry matching one label

    Args:
        item: Saved timetable item
        study_year_label: Target study-year label

    Returns:
        Matching study-year entry or None
    """
    entries = list(item.get("studyYearEntries") or [])
    for entry in entries:
        if str(entry.get("studyYearLabel") or "").strip() == str(study_year_label).strip():
            return entry
    return None


def _module_for_study_year(module_by_id: Dict[str, dict], fallback_module: dict | None, entry: dict | None) -> dict | None:
    """
    Resolves the effective module for one study-year entry

    Args:
        module_by_id: Modules indexed by id
        fallback_module: Fallback module data
        entry: Matching study-year entry

    Returns:
        Effective module data or None
    """
    module = dict(fallback_module or {})
    if entry is None:
        return module or None

    specific_module = module_by_id.get(_id_str(entry.get("moduleId")))
    if specific_module:
        module = dict(specific_module)

    if not module:
        return None

    module["typeOfDiscipline"] = "optional" if bool(entry.get("optional", False)) else "mandatory"
    module["pack"] = entry.get("pack", None)
    return module


def _display_title(module: dict | None, fallback_value: str) -> str:
    """
    Builds the displayed discipline title for one matrix cell

    Args:
        module: Effective module data
        fallback_value: Fallback title

    Returns:
        Display title
    """
    module = dict(module or {})
    category = str(module.get("category") or "").strip().lower()
    if category == "course" or category not in ("laboratory", "seminar"):
        return str(module.get("title") or fallback_value or "").strip()

    discipline = module.get("discipline") or {}
    return str(_dget(discipline, "acronym", None) or module.get("acronym") or fallback_value or "").strip()

def _flatten_modules(values) -> List[dict]:
    """
    Flattens nested module structures into a plain module list

    Args:
        values: Nested module values

    Returns:
        Flat module list
    """
    out: List[dict] = []

    def visit(value):
        """
        Visits nested module values during flattening

        Args:
            value: Nested module value

        Returns:
            None
        """
        if value is None:
            return

        if hasattr(value, "model_dump"):
            value = value.model_dump(mode="json")

        if isinstance(value, list):
            for item in value:
                visit(item)
            return

        if isinstance(value, dict):
            # case 1: this dict is already a module object
            if value.get("id") is not None:
                out.append(value)
                return

            # case 2: this is a map like {moduleId: moduleObject}
            for item in value.values():
                visit(item)
            return

    visit(values)
    return out

def _new_cell(day_id: str, day_name: str, hour_id: str, start: str, end: str, r: int, c: int) -> Dict[str, Any]:
    """
    Builds an empty study-year timetable cell

    Args:
        day_id: Day id
        day_name: Day name
        hour_id: Hour id
        start: Start hour
        end: End hour
        r: Row index
        c: Column index

    Returns:
        Empty timetable cell
    """
    return {
        "id": str(uuid.uuid4()),
        "module": None,
        "room": None,
        "day": {"id": day_id, "name": day_name},
        "hour": {"id": hour_id, "startHour": start, "endHour": end},
        "rowIndex": r,
        "columnIndex": c,
        "numberOfColumns": 1,
        "evenWeek": False,
        "oddWeek": False,
        "online": False,
        "showDisciplineTitle": "",
        "showTeacher": "",
        "hidden": False,
    }


def _is_occupied(cell: Dict[str, Any]) -> bool:
    """
    Checks whether a study-year cell is already occupied

    Args:
        cell: Matrix cell

    Returns:
        True when the cell is occupied
    """
    if not cell:
        return False
    if bool(cell.get("hidden")):
        return True
    if (cell.get("showTeacher") or "").strip():
        return True
    if (cell.get("showDisciplineTitle") or "").strip():
        return True
    if bool(cell.get("evenWeek")) or bool(cell.get("oddWeek")):
        return True
    if cell.get("module") is not None:
        return True
    if cell.get("room") is not None:
        return True
    return False


def _span_overlaps(row_cells: List[Dict[str, Any]], start: int, width: int) -> bool:
    """
    Checks whether a column span overlaps occupied cells

    Args:
        row_cells: Row cells
        start: Start column
        width: Column span width

    Returns:
        True when the span overlaps occupied cells
    """
    end = start + max(1, width)
    start = max(0, start)
    end = min(len(row_cells), end)
    for i in range(start, end):
        if _is_occupied(row_cells[i]):
            return True
    return False


def _ensure_row(
        rows: List[List[Dict[str, Any]]],
        need_row_index: int,
        day_id: str,
        day_name: str,
        hour_id: str,
        start: str,
        end: str,
        cols: int,
):
    """
    Ensures that a matrix contains the requested row index

    Args:
        rows: Matrix rows
        need_row_index: Required row index
        day_id: Day id
        day_name: Day name
        hour_id: Hour id
        start: Start hour
        end: End hour
        cols: Column count

    Returns:
        None
    """
    while len(rows) <= need_row_index:
        r = len(rows)
        rows.append([_new_cell(day_id, day_name, hour_id, start, end, r, c) for c in range(cols)])


def _activity_priority(item: Dict[str, Any], module_by_id: Dict[str, dict]) -> int:
    """
    Computes the placement priority used when ordering study-year items

    Args:
        item: Saved timetable item
        module_by_id: Modules indexed by id

    Returns:
        Sort priority for the item
    """
    module_id = _id_str(item.get("moduleId"))
    module = module_by_id.get(module_id) or {}
    category = str(module.get("category") or "").strip().lower()

    if category == "course":
        return 0
    if category in ("laboratory", "seminar", "labsem"):
        return 1
    return 1


def build_study_year_timetables_matrix(
        items: List[Dict[str, Any]],
        days: List[DayDTO],
        timeslots: List[TimeslotDTO],
        modules: List[ModuleDTO],
        rooms: List[RoomDTO],
) -> Dict[str, Dict[str, Dict[str, List[List[Dict[str, Any]]]]]]:
    """
    Builds study-year timetable matrices from saved timetable items

    Args:
        items: Saved timetable items
        days: Generation days
        timeslots: Generation timeslots
        modules: Available modules
        rooms: Available rooms

    Returns:
        Study-year timetable matrices
    """
    if items is None:
        raise ValueError("build_study_year_timetables_matrix received items=None")

    modules_plain = _flatten_modules(modules)
    rooms_plain = [_to_plain(r) for r in rooms]

    module_by_id = {
        _id_str(m.get("id")): m
        for m in modules_plain
        if isinstance(m, dict) and m.get("id") is not None
    }

    room_by_id = {
        _id_str(r.get("id")): r
        for r in rooms_plain
        if isinstance(r, dict) and r.get("id") is not None
    }

    day_ids = [_id_str(d.get("id")) for d in days if d.get("id") is not None]
    hour_ids = [_id_str(h.get("id")) for h in timeslots if h.get("id") is not None]

    day_meta = {
        _id_str(d.get("id")): (d.get("name") or "", i)
        for i, d in enumerate(days)
        if d.get("id") is not None
    }

    hour_meta = {
        _id_str(h.get("id")): (
            getattr(h, "startHour", None) or getattr(h, "start", "") or "",
            getattr(h, "endHour", None) or getattr(h, "end", "") or "",
            j,
        )
        for j, h in enumerate(timeslots)
        if h.get("id") is not None
    }

    sy_cols: Dict[str, int] = {}
    for x in items:
        raw_sy = (x.get("studyYearLabel") or "").strip()
        if not raw_sy:
            continue
        ci = int(x.get("columnIndex", 0) or 0)
        nc = int(x.get("numberOfColumns", 1) or 1)

        parts = _split_sy_labels(raw_sy)
        if len(parts) <= 1:
            sy_cols[raw_sy] = max(sy_cols.get(raw_sy, 0), ci + nc)
            continue

        per_part_cols = max(1, nc // len(parts))
        for part in parts:
            sy_cols[part] = max(sy_cols.get(part, 0), per_part_cols)

    if not sy_cols:
        sy_cols = {"SY?": 1}

    out: Dict[str, Dict[str, Dict[str, List[List[Dict[str, Any]]]]]] = {}
    for sy, cols in sy_cols.items():
        out[sy] = {}
        for did in day_ids:
            day_name, _ = day_meta[did]
            out[sy][did] = {}
            for hid in hour_ids:
                start, end, _ = hour_meta[hid]
                out[sy][did][hid] = [
                    [_new_cell(did, day_name, hid, start, end, 0, c) for c in range(cols)]
                ]

    ordered_items = sorted(
        items,
        key=lambda x: (
            str(x.get("studyYearLabel") or ""),
            str(x.get("dayId") or ""),
            str(x.get("hourId") or ""),
            _activity_priority(x, module_by_id),
            int(x.get("columnIndex", 0) or 0),
            str(x.get("moduleId") or ""),
        ),
    )

    for x in ordered_items:
        did = x.get("dayId")
        hid = x.get("hourId")
        raw_sy = (x.get("studyYearLabel") or "").strip()

        if not did or not hid or not raw_sy:
            continue

        did = str(did)
        hid = str(hid)
        split_labels = _split_sy_labels(raw_sy)
        if len(split_labels) > 1:
            target_labels = split_labels
        else:
            target_labels = [raw_sy]

        even_w = bool(x.get("evenWeek", False))
        odd_w = bool(x.get("oddWeek", False))

        if even_w and odd_w:
            even_w = False
            odd_w = False

        online = bool(x.get("online", False))
        show_disc = (x.get("showDisciplineTitle") or "").strip()
        show_teacher = (x.get("showTeacher") or "").strip()

        module_id = _id_str(x.get("moduleId"))
        room_id = _id_str(x.get("roomId"))

        module_obj = module_by_id.get(module_id)
        room_obj = room_by_id.get(room_id)

        for sy in target_labels:
            if sy not in out or did not in out[sy] or hid not in out[sy][did]:
                continue

            study_year_entry = _match_study_year_entry(x, sy)
            module_for_sy = _module_for_study_year(module_by_id, module_obj, study_year_entry)

            ci = int(x.get("columnIndex", 0) or 0)
            nc = int(x.get("numberOfColumns", 1) or 1)

            category = str((module_for_sy or {}).get("category") or "").strip().lower()
            if category == "course" or len(split_labels) > 1:
                ci = 0
                nc = sy_cols.get(sy, 1)

            rows = out[sy][did][hid]
            total_cols = len(rows[0])

            ci = max(0, ci)
            if ci >= total_cols:
                continue

            nc = max(1, nc)
            if ci + nc > total_cols:
                nc = total_cols - ci

            target_row = None
            for r_idx, row_cells in enumerate(rows):
                if not _span_overlaps(row_cells, ci, nc):
                    target_row = r_idx
                    break

            if target_row is None:
                day_name, _ = day_meta.get(did, ("", 0))
                start, end, _ = hour_meta.get(hid, ("", "", 0))
                _ensure_row(rows, len(rows), did, day_name, hid, start, end, total_cols)
                target_row = len(rows) - 1

            row_cells = rows[target_row]
            cell = row_cells[ci]

            cell["evenWeek"] = even_w
            cell["oddWeek"] = odd_w
            cell["online"] = online
            cell["showDisciplineTitle"] = _display_title(module_for_sy, show_disc)
            cell["showTeacher"] = show_teacher
            cell["numberOfColumns"] = nc
            cell["module"] = module_for_sy
            cell["room"] = room_obj
            cell["hidden"] = False

            for c in range(ci + 1, min(len(row_cells), ci + nc)):
                covered = row_cells[c]
                covered["evenWeek"] = False
                covered["oddWeek"] = False
                covered["online"] = False
                covered["showDisciplineTitle"] = ""
                covered["showTeacher"] = ""
                covered["numberOfColumns"] = 0
                covered["module"] = None
                covered["room"] = None
                covered["hidden"] = True

            for c in range(len(row_cells)):
                row_cells[c]["rowIndex"] = target_row

    return out
