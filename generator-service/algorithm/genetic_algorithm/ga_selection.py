from typing import List

import random as rn

from algorithm.algorithm_classes.GAIndividual import GAIndividual


def _tournament(pop: List[GAIndividual], k: int) -> GAIndividual:
    """
    Selects a parent with tournament selection

    Args:
        pop: Current GA population
        k: Tournament size

    Returns:
        Best individual sampled in the tournament
    """

    cand = rn.sample(pop, k=min(k, len(pop)))
    cand.sort(key=lambda ind: ind.fitness)
    return cand[0]
