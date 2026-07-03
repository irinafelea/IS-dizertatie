def print_matrix(matrix, rooms, days, timeslots, max_cell_width: int = 18):
    """
    Prints the scheduling matrix in a readable table format

    Args:
        matrix: Timetable matrix
        rooms: Available rooms
        days: Generation days
        timeslots: Generation timeslots
        max_cell_width: Maximum printed cell width

    Returns:
        None
    """

    def shorten(text: str, width: int) -> str:
        """
        Shortens one cell value to the requested width

        Args:
            text: Source text
            width: Maximum width

        Returns:
            Shortened text
        """
        text = str(text)
        return text if len(text) <= width else text[: width - 3] + "..."

    def cell_text(cell) -> str:
        """
        Resolves the printed text for one matrix cell

        Args:
            cell: Matrix cell

        Returns:
            Printed cell text
        """
        if cell is None:
            return "."

        if getattr(cell, "fixed", False):
            title = getattr(cell, "title", None) or "EVENT"
            return shorten(title, max_cell_width)

        if getattr(cell, "module", None) is not None:
            module = cell.module
            title = (
                    getattr(module, "title", None)
                    or getattr(module, "acronym", None)
                    or getattr(module, "id", None)
                    or "MODULE"
            )
            return shorten(title, max_cell_width)

        return "."

    room_headers = [shorten(getattr(r, "officialName", getattr(r, "id", "ROOM")), max_cell_width) for r in rooms]

    row_label_width = 22
    col_width = max_cell_width

    header = " " * row_label_width + " | " + " | ".join(h.ljust(col_width) for h in room_headers)
    sep = "-" * len(header)

    print(sep)
    print(header)
    print(sep)

    slots_per_day = len(timeslots)

    for row_idx, row in enumerate(matrix):
        day_idx = row_idx // slots_per_day
        slot_idx = row_idx % slots_per_day

        day_name = getattr(days[day_idx], "name", f"Day{day_idx}")
        ts = timeslots[slot_idx]
        start = getattr(ts, "startHour", "")
        end = getattr(ts, "endHour", "")

        try:
            start_str = start.strftime("%H:%M")
        except AttributeError:
            start_str = str(start)

        try:
            end_str = end.strftime("%H:%M")
        except AttributeError:
            end_str = str(end)

        row_label = f"{day_name} {start_str}-{end_str}"
        row_cells = " | ".join(cell_text(cell).ljust(col_width) for cell in row)
        print(row_label.ljust(row_label_width) + " | " + row_cells)

    print(sep)
