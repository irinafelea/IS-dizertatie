class MatrixCell:
    """
    Represents one timetable matrix cell

    Args:
        event: Fixed event stored in the cell
        module: Generated module stored in the cell
        fixed: Whether the cell is fixed and cannot be overwritten
        eventId: Identifier of the fixed event
        title: Display title for the fixed event
        room: Room label stored in the cell
        day: Day label stored in the cell
        hour: Timeslot label stored in the cell
        row: Matrix row index
        col: Matrix column index
        evenWeek: Whether the cell is occupied on even weeks
        oddWeek: Whether the cell is occupied on odd weeks

    Returns:
        None
    """
    def __init__(
        self,
        event=None,
        module=None,
        fixed=False,
        eventId=None,
        title=None,
        room=None,
        day=None,
        hour=None,
        row=None,
        col=None,
        evenWeek=False,
        oddWeek=False,
    ):
        self.event = event
        self.eventId = eventId
        self.title = title
        self.room = room
        self.day = day
        self.hour = hour

        self.module = module

        self.row = row
        self.col = col

        self.fixed = fixed
        self.evenWeek = evenWeek
        self.oddWeek = oddWeek

    def __repr__(self):
        """
        Builds the debug representation of the matrix cell

        Args:
            None

        Returns:
            Readable string representation of the cell
        """
        if self.fixed and self.event is not None:
            return f"[EVENT: {self.title}]"
        if self.module is not None:
            m = self.module
            if hasattr(m, "components"):
                sy = "+".join(c.studyYear.acronym for c in m.components)
                return f"[{m.acronym}-{m.teacher.lastName}-{sy}]"
            else:
                return f"[{m.acronym}-{m.teacher.lastName}-{m.studyYear.acronym}]"
        return "[ . ]"
