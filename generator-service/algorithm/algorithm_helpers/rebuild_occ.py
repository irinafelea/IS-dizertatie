from algorithm.algorithm_classes.Occ import Occ


def rebuild_occ(placements, timeslots, teacher_rules):
    """
    Rebuilds occupancy from the current placements

    Args:
        placements: Current placement list
        timeslots: All timetable timeslots
        teacher_rules: Teacher availability rules

    Returns:
        Occupancy rebuilt from the placed tasks
    """
    occ = Occ()
    for p in placements:
        if p is not None:
            occ.add(p, timeslots, teacher_rules)
    return occ
