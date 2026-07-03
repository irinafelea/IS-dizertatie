def print_tasks_stats(onsite_tasks, cells_cache):
    """
    Prints candidate-count statistics for tasks

    Args:
        onsite_tasks: Tasks to inspect
        cells_cache: Candidate-cell cache

    Returns:
        None
    """
    total_tasks = len(onsite_tasks)

    zero_cells = 0
    small_cells = 0
    stats = []

    for i, task in enumerate(onsite_tasks):
        n = len(cells_cache[i]) if i < len(cells_cache) else 0
        stats.append(n)

        if n == 0:
            zero_cells += 1
            print(
                f"[DEBUG][ZERO_CELLS] idx={i} task_id={task.id} category={task.category} duration={task.durationHours} sy={task.studyYearsLabels}")
        elif n < 5:
            small_cells += 1

    print(f"[DEBUG] total_tasks: {total_tasks}")
    print(f"[DEBUG] tasks with 0 candidates: {zero_cells}")
    print(f"[DEBUG] tasks with <5 candidates: {small_cells}")
