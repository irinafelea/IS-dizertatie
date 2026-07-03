import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from constants.parameters import (
    GA_POPULATION,
    GA_GENERATIONS,
    GA_ELITES,
    GA_TOURNAMENT_SIZE_K,
    GA_MUTATION_RATE,
    GA_MUTATION_SIGMA,
    LNS_FINAL_ITERATIONS,
    LNS_IMPROVEMENT_ITERATIONS,
    LNS_REMOVAL_SIZE,
    LNS_REINSERTION_TRY_LIMIT,
    GA_CONSTRUCT_CELL_TRIES,
    SA_INITIAL_TEMPERATURE,
    SA_COOLING_RATE,
)
from helpers.module import common_key, is_course


def _module_type_counts(modules: Iterable[object]) -> dict[str, int]:
    """
    Counts common and normal modules by activity type

    Args:
        modules: Source modules

    Returns:
        Module counts by category
    """
    counts = {
        "common_courses_count": 0,
        "normal_courses_count": 0,
        "common_labs_count": 0,
        "normal_labs_count": 0,
    }

    for module in modules:
        is_common = common_key(module) is not None
        if is_course(module):
            key = "common_courses_count" if is_common else "normal_courses_count"
        else:
            key = "common_labs_count" if is_common else "normal_labs_count"
        counts[key] += 1

    return counts


def _parameter_values() -> dict[str, Any]:
    """
    Builds the generation-parameter snapshot for CSV output

    Args:
        None

    Returns:
        Parameter values for metrics output
    """
    return {
        "GA_POPULATION": GA_POPULATION,
        "GA_GENERATIONS": GA_GENERATIONS,
        "GA_ELITES": GA_ELITES,
        "GA_TOURNAMENT_SIZE_K": GA_TOURNAMENT_SIZE_K,
        "GA_MUTATION_RATE": GA_MUTATION_RATE,
        "GA_MUTATION_SIGMA": GA_MUTATION_SIGMA,
        "LNS_FINAL_ITERATIONS": LNS_FINAL_ITERATIONS,
        "LNS_IMPROVEMENT_ITERATIONS": LNS_IMPROVEMENT_ITERATIONS,
        "LNS_REMOVAL_SIZE": LNS_REMOVAL_SIZE,
        "LNS_REINSERTION_TRY_LIMIT": LNS_REINSERTION_TRY_LIMIT,
        "GA_CONSTRUCT_CELL_TRIES": GA_CONSTRUCT_CELL_TRIES,
        "SA_INITIAL_TEMPERATURE": SA_INITIAL_TEMPERATURE,
        "SA_COOLING_RATE": SA_COOLING_RATE,
    }


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    """
    Reads CSV rows from disk when the file exists

    Args:
        path: CSV file path

    Returns:
        Existing CSV rows
    """
    if not path.exists():
        return []

    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def _write_appended_rows(path: Path, new_row: dict[str, Any]) -> None:
    """
    Rewrites the summary CSV with one appended row

    Args:
        path: Summary CSV path
        new_row: Row to append

    Returns:
        None
    """
    existing_rows = _read_csv_rows(path)
    fieldnames: list[str] = []
    preferred_tail = [
        "ga_fitness",
        "ga_runtime",
        "lns_fitness",
        "lns_runtime",
        "final_fitness",
        "time_to_best_seconds",
        "runtime_seconds",
        "total",
    ]
    ordered_new_keys = [key for key in new_row.keys() if key not in preferred_tail]

    for key in ordered_new_keys:
        if key not in fieldnames:
            fieldnames.append(key)

    for row in existing_rows:
        for key in row.keys():
            if key in preferred_tail or key in ("total_runtime_seconds", "ga_final_fitness"):
                continue
            if key not in fieldnames:
                fieldnames.append(key)

    for key in preferred_tail:
        if key not in fieldnames:
            fieldnames.append(key)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in existing_rows:
            normalized_row = {key: row.get(key, "") for key in fieldnames}
            if "ga_fitness" in fieldnames and not normalized_row.get("ga_fitness", ""):
                normalized_row["ga_fitness"] = row.get("ga_final_fitness", "")
            if "runtime_seconds" in fieldnames and not normalized_row.get("runtime_seconds", ""):
                normalized_row["runtime_seconds"] = row.get("total_runtime_seconds", "")
            writer.writerow(normalized_row)
        writer.writerow({key: new_row.get(key, "") for key in fieldnames})


def _append_history_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    """
    Appends history rows to the history CSV

    Args:
        path: History CSV path
        rows: History rows to append

    Returns:
        None
    """
    if not rows:
        return

    existing_rows = _read_csv_rows(path)
    fieldnames: list[str] = []

    for row in existing_rows + rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in existing_rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def save_generation_metrics_csv(
    semester_id: str,
    domain_id: str,
    version: int,
    modules: Iterable[object],
    metrics: dict[str, Any],
    output_dir: str = "files/generation-metrics",
) -> tuple[str, str]:
    """
    Saves generation summary and history metrics as CSV files

    Args:
        semester_id: Semester id
        domain_id: Domain id
        version: Timetable version
        modules: Source modules
        metrics: Collected generation metrics
        output_dir: Output directory path

    Returns:
        Summary CSV path and history CSV path
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_path = out_dir / "generation_summary.csv"
    history_path = out_dir / "generation_lns_history.csv"

    breakdown = dict(metrics.get("final_breakdown") or {})
    lns_history = list(metrics.get("lns_history") or [])

    row: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "semester_id": semester_id,
        "domain_id": domain_id,
        "version": version,
        "instance_name": metrics.get("instance_name"),
        "method_name": metrics.get("method_name"),
        "seed": metrics.get("seed"),
        "lns_destroy_mode": metrics.get("lns_destroy_mode"),
        "lns_repair_mode": metrics.get("lns_repair_mode"),
        "lns_size_mode": metrics.get("lns_size_mode"),
        **_parameter_values(),
        **_module_type_counts(modules),
        "ga_fitness": metrics.get("ga_final_fitness"),
        "ga_runtime": metrics.get("ga_final_runtime"),
        "lns_fitness": metrics.get("lns_fitness"),
        "lns_runtime": metrics.get("lns_runtime"),
        "final_fitness": metrics.get("final_fitness"),
        "time_to_best_seconds": metrics.get("time_to_best_seconds"),
        "runtime_seconds": metrics.get("runtime_seconds"),
    }

    for key in sorted(breakdown):
        row[key] = breakdown[key]

    _write_appended_rows(summary_path, row)

    history_rows: list[dict[str, Any]] = []
    for point in lns_history:
        history_rows.append(
            {
                "semester_id": semester_id,
                "domain_id": domain_id,
                "version": version,
                "instance_name": metrics.get("instance_name"),
                "method_name": metrics.get("method_name"),
                "seed": metrics.get("seed"),
                "iteration": point.get("iteration"),
                "elapsed_seconds": point.get("elapsed_seconds"),
                "best_fitness": point.get("best_fitness"),
                "current_fitness": point.get("current_fitness"),
                "destroy_operator": point.get("destroy_operator"),
                "repair_operator": point.get("repair_operator"),
                "remove_k": point.get("remove_k"),
                "accepted": point.get("accepted"),
                "reward": point.get("reward"),
            }
        )

    _append_history_rows(history_path, history_rows)

    return str(summary_path), str(history_path)
