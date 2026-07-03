from collections import Counter

from algorithm.algorithm_helpers.can_place import can_place

from helpers.module import is_course, is_master_module, module_hours, discipline_uuid
from helpers.teacher import teacher_uuid
from helpers.timetable import is_cell_blocked, row_to_day_time
from helpers.task_module_target import target_semantics_for_study_year
from algorithm.hard_constraints.room_allows_task import room_allows_task
from algorithm.soft_constraints.optional_overlap_allowed import optional_overlap_allowed
from constants.algorithm import MASTER_MIN_SLOT_INDEX


def explain_can_place_failure(
        occ,
        task,
        row,
        col,
        parity_mask,
        base_matrix,
        rooms,
        timeslots,
        teacher_rules,
        teacher_task_counts,
):
    """
    Explains why one candidate placement fails hard checks

    Args:
        occ: Current occupancy
        task: Candidate task
        row: Candidate row
        col: Candidate column
        parity_mask: Candidate parity mask
        base_matrix: Base timetable matrix
        rooms: Available rooms
        timeslots: Generation timeslots
        teacher_rules: Teacher rules map
        teacher_task_counts: Task counts by teacher

    Returns:
        Failure reason label
    """
    m = task.modules[0]

    if is_cell_blocked(base_matrix, row, col):
        return "blocked_cell"

    _, slot_idx = row_to_day_time(row, timeslots)
    if is_master_module(m) and slot_idx < MASTER_MIN_SLOT_INDEX:
        return "master_too_early"

    if not room_allows_task(rooms[col], task, rooms):
        return "room_capacity"

    if occ._mask_has_overlap(occ.room_mask.get((row, col), 0), parity_mask):
        return "room_overlap"

    tid = teacher_uuid(m)

    if tid and occ._mask_has_overlap(occ.teacher_row_mask.get((tid, row), 0), parity_mask):
        return "teacher_overlap"

    if tid and tid in teacher_rules:
        rules = teacher_rules[tid]

        if row in rules["forbidden_rows"]:
            return "teacher_forbidden"

        mandatory_rows = rules["mandatory_rows"]
        if mandatory_rows:
            total_modules = teacher_task_counts.get(tid, 0)
            used_mandatory = occ.teacher_mandatory_used.get(tid, 0)

            if total_modules <= len(mandatory_rows):
                if row not in mandatory_rows:
                    return "teacher_outside_mandatory"
            else:
                if used_mandatory < len(mandatory_rows) and row not in mandatory_rows:
                    return "teacher_mandatory_not_filled_yet"

    if is_course(m):
        for sy in task.studyYearsIds:
            semantics = target_semantics_for_study_year(task, 0, sy, m)
            target_pack = semantics.get("pack", None)
            target_discipline_id = str(semantics.get("disciplineId") or discipline_uuid(m) or "")
            existing_course = occ._mask_has_overlap(
                occ.sy_course_row_mask.get((sy, row), 0), parity_mask
            )
            existing_lab = occ._mask_has_overlap(
                occ.sy_any_lab_row_mask.get((sy, row), 0), parity_mask
            )

            if not getattr(m, "optional", False):
                if existing_course or existing_lab:
                    return f"mandatory_course_overlap_sy={sy}"
            else:
                if existing_course or existing_lab:
                    if not optional_overlap_allowed(occ, row, parity_mask, sy, target_pack, target_discipline_id):
                        return f"optional_course_overlap_not_allowed_sy={sy}"

        return "unknown_course_failure"

    sy = task.studyYearsIds[0]
    gi = task.groupIndex
    if gi is None:
        return "lab_without_group"

    existing_course = occ._mask_has_overlap(
        occ.sy_course_row_mask.get((sy, row), 0), parity_mask
    )
    existing_group = occ._mask_has_overlap(
        occ.sy_group_row_mask.get((sy, int(gi), row), 0), parity_mask
    )

    if getattr(m, "optional", False):
        semantics = target_semantics_for_study_year(task, 0, sy, m)
        target_pack = semantics.get("pack", None)
        target_discipline_id = str(semantics.get("disciplineId") or discipline_uuid(m) or "")
        if existing_course or existing_group:
            if not optional_overlap_allowed(occ, row, parity_mask, sy, target_pack, target_discipline_id):
                return f"optional_lab_overlap_not_allowed_sy={sy}_group={gi}"
    else:
        if existing_course:
            return f"mandatory_lab_course_overlap_sy={sy}"
        if existing_group:
            return f"mandatory_lab_group_overlap_sy={sy}_group={gi}"
        return "unknown_mandatory_lab_failure"

    return "unknown_failure"


def diagnose_failed_task(task, cells, occ, base_matrix, rooms, timeslots, teacher_rules, teacher_task_counts, current_placements, days):
    """
    Prints diagnostics for a task that could not be placed

    Args:
        task: Failed task
        cells: Candidate cells
        occ: Current occupancy
        base_matrix: Base timetable matrix
        rooms: Available rooms
        timeslots: Generation timeslots
        teacher_rules: Teacher rules map
        teacher_task_counts: Task counts by teacher
        current_placements: Current placements
        days: Generation days

    Returns:
        None
    """

    masks = [3] if module_hours(task.modules[0]) >= 2 else [1, 2]
    module_order = None
    reasons = Counter()
    ok_count = 0

    for r, c in cells:
        for mask in masks:
            ok = can_place(
                occ=occ,
                task=task,
                row=r,
                col=c,
                parity_mask=mask,
                module_order=module_order,
                base_matrix=base_matrix,
                rooms=rooms,
                timeslots=timeslots,
                teacher_rules=teacher_rules,
                teacher_task_counts=teacher_task_counts,
                days=days,
            )

            if ok:
                ok_count += 1
            else:
                reason = explain_can_place_failure(
                    occ, task, r, c, mask,
                    base_matrix, rooms, timeslots,
                    teacher_rules, teacher_task_counts
                )
                reasons[reason] += 1

    title = task.modules[0].title if task.modules else str(task.id)
    teacher = getattr(task.modules[0], "completeTeacher", "") if task.modules else ""
    print(f"[FAILED TASK] {title} - {teacher} | {task.studyYearsLabels} | {task.category} | {task.durationHours}h")
    # print(f"[FAILED TASK] candidate_cells={len(cells)} feasible_variants={ok_count}")
    # for reason, count in reasons.most_common():
    #     print(f"[FAILED TASK] {reason}: {count}")

    for r, c in cells[:20]:
        for mask in masks:
            ok = can_place(
                occ=occ,
                task=task,
                row=r,
                col=c,
                parity_mask=mask,
                module_order=module_order,
                base_matrix=base_matrix,
                rooms=rooms,
                timeslots=timeslots,
                teacher_rules=teacher_rules,
                teacher_task_counts=teacher_task_counts,
                days=days,
            )

            room = rooms[c] if 0 <= c < len(rooms) else {}
            room_name = room.get("name") or room.get("officialName") or ""

            if ok:
                print(f"[FAILED TASK] TRY row={r} room_col={c} room={room_name} mask={mask} ok=True")
                continue

            reason = explain_can_place_failure(
                occ, task, r, c, mask,
                base_matrix, rooms, timeslots,
                teacher_rules, teacher_task_counts
            )
            print(f"[FAILED TASK] TRY row={r} room_col={c} room={room_name} mask={mask} reason={reason}")

            if reason == "room_overlap":
                diagnose_room_overlap(current_placements, r, c, mask)
            if "overlap" in reason:
                diagnose_student_overlap(task, current_placements, r, mask)

def diagnose_room_overlap(placements, row, col, parity_mask):
    """
    Prints placements that overlap one room cell

    Args:
        placements: Current placements
        row: Candidate row
        col: Candidate column
        parity_mask: Candidate parity mask

    Returns:
        None
    """
    print(f"    [ROOM OCCUPANTS] row={row} col={col} mask={parity_mask}")
    for p in placements:
        if p is None:
            continue
        if p.row == row and p.col == col:
            overlap = (p.parity_mask & parity_mask) != 0
            print(
                f"      task={p.task.id} "
                f"title={getattr(p.module, 'title', p.module)} "
                f"parity={p.parity_mask} overlap={overlap}"
            )


def diagnose_student_overlap(task, placements, row, parity_mask):
    """
    Prints placements that overlap one student group or study year

    Args:
        task: Failed task
        placements: Current placements
        row: Candidate row
        parity_mask: Candidate parity mask

    Returns:
        None
    """
    target_sy = set(str(x) for x in (task.studyYearsIds or []))
    target_group = task.groupIndex

    print(f"    [STUDENT OCCUPANTS] row={row} mask={parity_mask}")
    for p in placements:
        if p is None or p.row != row:
            continue
        if (p.parity_mask & parity_mask) == 0:
            continue

        other_sy = set(str(x) for x in (p.task.studyYearsIds or []))
        if not (target_sy & other_sy):
            continue

        same_group = True
        if task.category == "labsem" and p.task.category == "labsem":
            if target_group is None or p.task.groupIndex is None:
                same_group = False
            else:
                same_group = int(target_group) == int(p.task.groupIndex)

        if task.category == "course" or p.task.category == "course" or same_group:
            print(
                f"      task={p.task.id} title={getattr(p.module, 'title', p.module)} "
                f"teacher={getattr(p.module, 'completeTeacher', '')} "
                f"category={p.task.category} sy={p.task.studyYearsLabels} "
                f"group={p.task.groupIndex} parity={p.parity_mask} room_col={p.col}"
            )
