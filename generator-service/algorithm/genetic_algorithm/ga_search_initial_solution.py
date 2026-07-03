from typing import Tuple, List, Optional
import time

import random as rn

from algorithm.algorithm_classes.GAIndividual import GAIndividual
from algorithm.algorithm_classes.Placement import Placement
from app.models.TaskDTO import TaskDTO
from constants.parameters import GA_POPULATION, GA_GENERATIONS, GA_ELITES, GA_TOURNAMENT_SIZE_K
from algorithm.genetic_algorithm._order_from_keys import _order_from_keys
from algorithm.genetic_algorithm.construct_feasible_solution import construct_feasible_solution
from algorithm.genetic_algorithm.ga_crossover import _crossover
from algorithm.genetic_algorithm.ga_fitness import _evaluate_individual, _evaluate_initial_individual
from algorithm.genetic_algorithm.ga_mutation import _mutate
from algorithm.genetic_algorithm.ga_selection import _tournament
from algorithm.large_neighbourhood_search.lns_placement_consensus_ratio import (
    build_elite_placement_frequencies,
    build_population_consensus,
)
from printers.debug_score_solution import log_debug_individual


def ga_search_best_initial_solution(
        tasks: List[TaskDTO],
        base_matrix,
        rooms,
        days,
        timeslots,
        cells_cache,
        teachers_availabilities,
        teacher_task_counts,
        pop_size: int = GA_POPULATION,
        gens: int = GA_GENERATIONS,
        enforce_bachelor_third_year_free_day: bool = False,
) -> Tuple[List[Optional[Placement]], int, dict]:
    """
    Runs the genetic algorithm to build the initial timetable solution

    Args:
        tasks: All tasks from the timetable instance
        base_matrix: Base matrix with blocked cells
        rooms: All available rooms
        days: All timetable days
        timeslots: All timetable timeslots
        cells_cache: Cached candidate cells by task
        teachers_availabilities: Teacher availability rules
        teacher_task_counts: Number of tasks per teacher
        pop_size: GA population size
        gens: Number of GA generations
        enforce_bachelor_third_year_free_day: Whether to enforce third-year free-day penalties

    Returns:
        Placements, best GA fitness, and GA metadata
    """

    t_start = time.perf_counter()
    n = len(tasks)
    pop = [GAIndividual(keys=[rn.random() for _ in range(n)]) for _ in range(pop_size)]

    for ind in pop:
        ind.fitness = _evaluate_initial_individual(
            ind,
            tasks,
            base_matrix,
            rooms,
            days,
            timeslots,
            cells_cache,
            teachers_availabilities,
            teacher_task_counts,
            enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
        )

    best = min(pop, key=lambda x: x.fitness)
    print(f"[GA] initial fitness={best.fitness} t={time.perf_counter() - t_start:.4f} seconds")

    for g in range(gens):
        t_start_generation = time.perf_counter()
        pop.sort(key=lambda x: x.fitness)
        elites = pop[: min(GA_ELITES, len(pop))]
        new_pop = elites[:]

        while len(new_pop) < pop_size:
            p1 = _tournament(pop, GA_TOURNAMENT_SIZE_K)
            p2 = _tournament(pop, GA_TOURNAMENT_SIZE_K)
            child = _crossover(p1, p2)
            _mutate(child)
            child.fitness = _evaluate_individual(
                child,
                tasks,
                base_matrix,
                rooms,
                days,
                timeslots,
                cells_cache,
                teachers_availabilities,
                teacher_task_counts,
                enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
            )
            new_pop.append(child)

        pop = new_pop
        pop.sort(key=lambda x: x.fitness)
        cur_best = pop[0]
        if cur_best.fitness < best.fitness:
            best = cur_best

        print(
            f"[GA] gen={g + 1}/{gens} best={best.fitness}  "
            f"cur_best={cur_best.fitness} t={time.perf_counter() - t_start_generation:.4f} seconds"
        )
        if g % 9 == 0:
            log_debug_individual(
                best,
                tasks,
                base_matrix,
                rooms,
                days,
                timeslots,
                cells_cache,
                teachers_availabilities,
                teacher_task_counts,
                enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
                prefix=f"[GA][gen={g + 1}]",
            )

    order = _order_from_keys(tasks, cells_cache, best.keys)
    placements = construct_feasible_solution(tasks, base_matrix, rooms, days, timeslots, cells_cache, order, teachers_availabilities, teacher_task_counts)

    pop.sort(key=lambda x: x.fitness)
    archive_size = min(max(GA_ELITES * 2, 8), len(pop))
    elite_solutions: list[list[Optional[Placement]]] = []
    for ind in pop[:archive_size]:
        elite_order = _order_from_keys(tasks, cells_cache, ind.keys)
        elite_placements = construct_feasible_solution(
            tasks,
            base_matrix,
            rooms,
            days,
            timeslots,
            cells_cache,
            elite_order,
            teachers_availabilities,
            teacher_task_counts,
        )
        if all(p is not None for p in elite_placements):
            elite_solutions.append(elite_placements)

    elite_placement_frequencies = build_elite_placement_frequencies(elite_solutions)
    population_consensus = build_population_consensus(elite_solutions)
    ga_metadata = {
        "elite_solution_count": len(elite_solutions),
        "elite_placement_frequencies": elite_placement_frequencies,
        "population_consensus": population_consensus,
    }
    return placements, best.fitness, ga_metadata
