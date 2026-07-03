from __future__ import annotations

import math
from typing import Iterable


def init_ucb_state(arms: Iterable[str]) -> dict:
    """
    Initializes the UCB state for adaptive operator selection

    Args:
        arms: Available operator choices

    Returns:
        UCB state with counts, rewards, and total selections
    """
    arm_list = [str(a) for a in arms]
    return {
        "total": 0,
        "counts": {arm: 0 for arm in arm_list},
        "rewards": {arm: 0.0 for arm in arm_list},
    }

def choose_ucb_option(state: dict, arms: Iterable[str]) -> str:
    """
    Selects the next operator with the UCB rule

    Args:
        state: Current UCB state
        arms: Available operator choices

    Returns:
        Selected operator name
    """
    arm_list = [str(a) for a in arms]
    counts = state.setdefault("counts", {})
    rewards = state.setdefault("rewards", {})
    total = int(state.get("total") or 0)

    for arm in arm_list:
        if int(counts.get(arm, 0)) <= 0:
            return arm

    best_arm = arm_list[0]
    best_score = float("-inf")
    log_term = math.log(max(1, total))
    for arm in arm_list:
        count = max(1, int(counts.get(arm, 0)))
        mean_reward = float(rewards.get(arm, 0.0)) / float(count)
        bonus = math.sqrt((2.0 * log_term) / float(count))
        score = mean_reward + bonus
        if score > best_score:
            best_score = score
            best_arm = arm
    return best_arm

def update_ucb_state(state: dict, arm: str, reward: float) -> None:
    """
    Updates the UCB state after an operator is used

    Args:
        state: Current UCB state
        arm: Operator that was selected
        reward: Reward assigned to the operator

    Returns:
        None
    """
    state["total"] = int(state.get("total") or 0) + 1
    counts = state.setdefault("counts", {})
    rewards = state.setdefault("rewards", {})
    counts[arm] = int(counts.get(arm, 0)) + 1
    rewards[arm] = float(rewards.get(arm, 0.0)) + float(reward)

def normalized_reward(previous_score: int, candidate_score: int, accepted: bool, improved_best: bool) -> float:
    """
    Computes the adaptive reward for one LNS iteration

    Args:
        previous_score: Score before the move
        candidate_score: Score after the move
        accepted: Whether the move was accepted
        improved_best: Whether the move improved the best solution

    Returns:
        Reward used to update the adaptive selectors
    """
    if previous_score <= 0:
        baseline = 1.0
    else:
        baseline = float(previous_score)

    improvement = max(0.0, float(previous_score - candidate_score) / baseline)
    reward = improvement
    if accepted:
        reward += 0.02
    if improved_best:
        reward += 0.08
    return reward
