from algorithm.algorithm_classes.Occ import Occ


def optional_overlap_allowed(occ, row, parity_mask, study_year_id, pack, discipline_id) -> bool:
    """
    Checks whether an optional overlap is allowed

    Args:
        occ: Current occupancy state
        row: Candidate row
        parity_mask: Candidate parity mask
        study_year_id: Study year identifier
        pack: Optional pack identifier
        discipline_id: Discipline identifier

    Returns:
        True if the overlap is allowed
    """
    if pack is None or not discipline_id:
        return False

    overlapping_optional = False
    for other_pack, other_discipline_id, other_mask, _ in occ.sy_optional_entries.get((str(study_year_id), row), []):
        if not Occ._mask_has_overlap(other_mask, parity_mask):
            continue
        overlapping_optional = True
        if int(other_pack) != int(pack):
            return False
        if str(other_discipline_id) == str(discipline_id):
            return False

    return overlapping_optional
