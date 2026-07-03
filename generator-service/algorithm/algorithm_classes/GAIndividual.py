
from dataclasses import dataclass
from typing import List

from constants.algorithm import VERY_LARGE_SCORE

@dataclass
class GAIndividual:
    """
    Stores one GA individual and its fitness value
    """
    keys: List[float]
    fitness: int = VERY_LARGE_SCORE
