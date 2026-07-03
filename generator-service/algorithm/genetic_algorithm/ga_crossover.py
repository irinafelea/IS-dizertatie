import random as rn

from algorithm.algorithm_classes.GAIndividual import GAIndividual
from constants.parameters import GA_CROSSOVER_RATE


def _crossover(a: GAIndividual, b: GAIndividual) -> GAIndividual:
    """
    Combines two GA individuals with uniform crossover

    Args:
        a: First parent
        b: Second parent

    Returns:
        Child individual created from the parent keys
    """

    n = len(a.keys)
    child = [a.keys[i] if rn.random() < GA_CROSSOVER_RATE else b.keys[i] for i in range(n)]
    return GAIndividual(keys=child)
