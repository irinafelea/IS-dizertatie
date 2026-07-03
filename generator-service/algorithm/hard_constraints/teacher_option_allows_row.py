def teacher_option_allows_row(teacher_rules: dict, teacher_id: str, row: int) -> bool:
    """
    Checks whether a teacher can be placed on a row

    Args:
        teacher_rules: Teacher availability rules
        teacher_id: Teacher identifier
        row: Candidate timetable row

    Returns:
        True if the row is not forbidden for the teacher
    """
    teacher_id = str(teacher_id)
    if teacher_id not in teacher_rules:
        return True
    rules = teacher_rules[teacher_id]
    return row not in rules["forbidden_rows"]
