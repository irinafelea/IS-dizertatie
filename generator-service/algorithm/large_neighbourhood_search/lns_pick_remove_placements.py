from typing import Optional, List
import random as rn

from algorithm.algorithm_classes.Placement import Placement
from algorithm.algorithm_helpers.paired_one_hour import build_one_hour_pair_index
from algorithm.algorithm_score.score_solution import score_solution
from algorithm.large_neighbourhood_search.lns_group_week_helpers import (
    build_group_week_counts,
    compute_parity_imbalance_impact,
)
from algorithm.large_neighbourhood_search.lns_placement_local_cost import lns_placement_local_cost
from algorithm.soft_constraints.bachelor_third_year_course_days_penalty import (
    bachelor_third_year_course_day_over_limit_burden,
    bachelor_third_year_modules_day_over_limit_burden,
)
from algorithm.large_neighbourhood_search.lns_placement_consensus_ratio import compute_elite_placement_frequency_ratio
from app.models.TimeslotDTO import TimeslotDTO
from constants.parameters import LNS_REMOVAL_SIZE


def lns_pick_remove_placements(
        cur: List[Optional[Placement]],
        timeslots: List[TimeslotDTO],
        teachers_availabilities,
        tasks=None,
        enforce_bachelor_third_year_free_day: bool = False,
        remove_k: int = LNS_REMOVAL_SIZE,
        elite_placement_frequencies: dict | None = None,
        destroy_operator: str = "population",
) -> List[int]:
    """
    Selects placements to remove during the LNS destroy phase

    Args:
        cur: Current placement list
        timeslots: All timetable timeslots
        teachers_availabilities: Teacher availability rules
        tasks: All tasks from the timetable instance
        enforce_bachelor_third_year_free_day: Whether to enforce third-year free-day penalties
        remove_k: Target number of removals
        elite_placement_frequencies: Elite placement frequencies from GA
        destroy_operator: Destroy strategy to use

    Returns:
        Task indices selected for removal
    """
    pair_index = build_one_hour_pair_index(tasks or []) if tasks is not None else {}
    group_week_counts = build_group_week_counts(cur)

    present = [i for i, p in enumerate(cur) if p is not None]
    if not present:
        return []

    before = score_solution(
        cur,
        timeslots,
        teachers_availabilities,
        enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
    )

    def parity_burden(i: int) -> int:
        return compute_parity_imbalance_impact(group_week_counts, cur[i])

    def third_year_burden(i: int) -> int:
        if not enforce_bachelor_third_year_free_day:
            return 0
        spd = len(timeslots)
        return (
            bachelor_third_year_course_day_over_limit_burden(cur[i], cur, spd)
            + bachelor_third_year_modules_day_over_limit_burden(cur[i], cur, spd)
        )

    def local_cost(i: int) -> float:
        return lns_placement_local_cost(
            cur[i],
            timeslots,
            placements=cur,
            teachers_availabilities=teachers_availabilities,
            enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
        )

    def instability(i: int) -> float:
        return 1.0 - compute_elite_placement_frequency_ratio(elite_placement_frequencies, i, cur[i])

    damage_cache: dict[int, int] = {}

    def damage(i: int) -> int:
        cached = damage_cache.get(i)
        if cached is not None:
            return cached
        saved = cur[i]
        cur[i] = None
        after = score_solution(
            cur,
            timeslots,
            teachers_availabilities,
            enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
        )
        cur[i] = saved
        delta = before - after
        damage_cache[i] = delta
        return delta

    def cheap_conflict_key(i: int):
        return (
            parity_burden(i),
            third_year_burden(i),
            local_cost(i),
            instability(i),
        )

    def cheap_population_key(i: int):
        return (
            instability(i),
            parity_burden(i),
            third_year_burden(i),
            local_cost(i),
        )

    if destroy_operator == "random":
        pool = rn.sample(present, k=min(len(present), max(remove_k * 4, 40)))
    elif destroy_operator == "conflict":
        pre_ranked = sorted(
            present,
            key=cheap_conflict_key,
            reverse=True,
        )
        strong = pre_ranked[:min(len(pre_ranked), max(remove_k * 3, 30))]
        strong.sort(
            key=lambda i: (
                damage(i),
                parity_burden(i),
                third_year_burden(i),
                local_cost(i),
                instability(i),
            ),
            reverse=True,
        )
        pool = strong
    else:
        pre_ranked = sorted(
            present,
            key=cheap_population_key,
            reverse=True,
        )
        strong = pre_ranked[:min(len(pre_ranked), max(remove_k * 3, 30))]
        strong.sort(
            key=lambda i: (
                instability(i),
                damage(i),
                parity_burden(i),
                third_year_burden(i),
                local_cost(i),
            ),
            reverse=True,
        )
        pool = strong

    pool_set = set(pool)
    remainder = [i for i in present if i not in pool_set]

    if remainder:
        filler = rn.sample(remainder, k=min(len(remainder), 12))
        if destroy_operator == "conflict":
            filler.sort(key=cheap_conflict_key, reverse=True)
        elif destroy_operator == "population":
            filler.sort(key=cheap_population_key, reverse=True)
        pool += filler

    if destroy_operator == "random":
        rn.shuffle(pool)

    target_k = min(remove_k, len(present))
    selected: list[int] = []
    selected_set: set[int] = set()

    for idx in pool:
        if idx in selected_set:
            continue
        if len(selected) >= target_k:
            break

        selected.append(idx)
        selected_set.add(idx)

        partner_idx = pair_index.get(idx)
        if partner_idx is not None and partner_idx in present and partner_idx not in selected_set:
            if len(selected) < target_k:
                selected.append(partner_idx)
                selected_set.add(partner_idx)

    return selected
