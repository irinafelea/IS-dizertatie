import math
import random as rn


def lns_accept_move(new_score: int, current_score: int, temp: float) -> bool:
    """
    Decides whether an LNS move should be accepted

    Args:
        new_score: Candidate solution score
        current_score: Current solution score
        temp: Current simulated annealing temperature

    Returns:
        True if the candidate move should be accepted
    """

    if new_score < current_score:
        return True
    if temp <= 1e-9:
        return False
    return rn.random() < math.exp(-(new_score - current_score) / temp)
