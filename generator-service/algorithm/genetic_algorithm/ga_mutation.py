import random as rn

from algorithm.algorithm_classes.GAIndividual import GAIndividual
from constants.parameters import GA_MUTATION_RATE, GA_MUTATION_SIGMA


def _mutate(ind: GAIndividual) -> None:
    """
    Applies Gaussian mutation to a GA individual

    Args:
        ind: Individual to mutate

    Returns:
        None
    """

    for i in range(len(ind.keys)):
        if rn.random() < GA_MUTATION_RATE:
            ind.keys[i] += rn.gauss(0.0, GA_MUTATION_SIGMA)
