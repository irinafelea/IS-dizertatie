from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Tuple

from algorithm.algorithm_classes.Placement import Placement

PlacementSignature = Tuple[int, int, int, tuple[int, ...] | None, int | None]
PerTaskPlacementFrequencies = Dict[int, Counter]


def placement_key(p: Optional[Placement]) -> Optional[PlacementSignature]:
    """
    Builds the stable key used to count one placement

    Args:
        p: Placement to encode

    Returns:
        Placement key used in elite frequency tracking
    """
    if p is None:
        return None
    module_order = tuple(p.module_order) if p.module_order is not None else None
    group_index = getattr(p.task, "groupIndex", None)
    return (int(p.row), int(p.col), int(p.parity_mask), module_order, group_index)


def placement_signature(p: Optional[Placement]) -> Optional[PlacementSignature]:
    """
    Compatibility wrapper for placement_key

    Args:
        p: Placement to encode

    Returns:
        Placement key used in elite frequency tracking
    """
    return placement_key(p)


def build_elite_placement_frequencies(elite_solutions: List[List[Optional[Placement]]]) -> dict:
    """
    Builds placement frequencies from elite solutions

    Args:
        elite_solutions: Elite solutions collected from GA

    Returns:
        Placement frequency structure indexed by task
    """
    placement_counts_by_task: PerTaskPlacementFrequencies = {}
    elite_solution_count = 0

    for solution in elite_solutions:
        if not solution:
            continue

        elite_solution_count += 1
        for task_idx, placement in enumerate(solution):
            key = placement_key(placement)
            if key is None:
                continue
            placement_counts_by_task.setdefault(task_idx, Counter())[key] += 1

    return {
        "elite_solution_count": elite_solution_count,
        "placement_counts_by_task": placement_counts_by_task,
    }


def build_population_consensus(elite_solutions: List[List[Optional[Placement]]]) -> dict:
    """
    Builds the legacy consensus structure from elite solutions

    Args:
        elite_solutions: Elite solutions collected from GA

    Returns:
        Consensus structure with both legacy and renamed keys
    """
    frequencies = build_elite_placement_frequencies(elite_solutions)
    return {
        "total": frequencies["elite_solution_count"],
        "per_task": frequencies["placement_counts_by_task"],
        "elite_solution_count": frequencies["elite_solution_count"],
        "placement_counts_by_task": frequencies["placement_counts_by_task"],
    }


def compute_elite_placement_frequency_ratio(
        elite_placement_frequencies: dict | None,
        task_idx: int,
        placement: Optional[Placement],
) -> float:
    """
    Computes the elite placement agreement ratio for one task

    Args:
        elite_placement_frequencies: Elite placement frequency structure
        task_idx: Task index being evaluated
        placement: Placement to compare

    Returns:
        Agreement ratio for the placement among elite solutions
    """
    if not elite_placement_frequencies or not placement:
        return 0.0

    elite_solution_count = int(
        elite_placement_frequencies.get("elite_solution_count")
        or elite_placement_frequencies.get("total")
        or 0
    )
    if elite_solution_count <= 0:
        return 0.0

    placement_counts_by_task: PerTaskPlacementFrequencies = (
        elite_placement_frequencies.get("placement_counts_by_task")
        or elite_placement_frequencies.get("per_task")
        or {}
    )

    key = placement_key(placement)
    if key is None:
        return 0.0

    return float(placement_counts_by_task.get(task_idx, Counter()).get(key, 0)) / float(elite_solution_count)


def placement_consensus_ratio(consensus: dict | None, task_idx: int, placement: Optional[Placement]) -> float:
    """
    Compatibility wrapper for elite placement agreement ratio

    Args:
        consensus: Legacy consensus structure
        task_idx: Task index being evaluated
        placement: Placement to compare

    Returns:
        Agreement ratio for the placement among elite solutions
    """
    return compute_elite_placement_frequency_ratio(consensus, task_idx, placement)


def summarize_stable_assignments(
        elite_placement_frequencies: dict | None,
        placements: List[Optional[Placement]],
        minimum_elite_agreement_ratio: float = 0.6,
) -> dict:
    """
    Summarizes how many current placements are stable across elite solutions

    Args:
        elite_placement_frequencies: Elite placement frequency structure
        placements: Current placement list
        minimum_elite_agreement_ratio: Minimum ratio required to mark an assignment as stable

    Returns:
        Stable assignment count and ratio
    """
    if not elite_placement_frequencies:
        return {"stable_assignment_count": 0, "stable_assignment_ratio": 0.0}

    present_assignment_count = 0
    stable_assignment_count = 0
    for task_idx, placement in enumerate(placements):
        if placement is None:
            continue
        present_assignment_count += 1
        if compute_elite_placement_frequency_ratio(
                elite_placement_frequencies,
                task_idx,
                placement,
        ) >= minimum_elite_agreement_ratio:
            stable_assignment_count += 1

    return {
        "stable_assignment_count": stable_assignment_count,
        "stable_assignment_ratio": (
            float(stable_assignment_count) / float(present_assignment_count)
        ) if present_assignment_count else 0.0,
    }


def summarize_backbone(consensus: dict | None, placements: List[Optional[Placement]], threshold: float = 0.6) -> dict:
    """
    Compatibility wrapper for stable assignment statistics

    Args:
        consensus: Legacy consensus structure
        placements: Current placement list
        threshold: Minimum agreement ratio

    Returns:
        Stable assignment statistics with legacy backbone aliases
    """
    stable_assignment_stats = summarize_stable_assignments(consensus, placements, threshold)
    return {
        "backbone_assignments": stable_assignment_stats["stable_assignment_count"],
        "backbone_ratio": stable_assignment_stats["stable_assignment_ratio"],
        "stable_assignment_count": stable_assignment_stats["stable_assignment_count"],
        "stable_assignment_ratio": stable_assignment_stats["stable_assignment_ratio"],
    }
