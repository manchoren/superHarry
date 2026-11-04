#!/usr/bin/env python3
"""Show project task progress and the next task in the delivery queue."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

TASK_LINE = re.compile(
    r"^- \[(?P<checked>[ xX])\] \*\*(?P<task_id>T\d+)"
    r"(?:\s+-\s+(?P<title>.*?))?\*\*"
)
QUEUE_LINE = re.compile(r"^\|\s*\d+\s*\|\s*(T\d+)\s*\|\s*(.*?)\s*\|")
STATUS = re.compile(r"\bStatus:\s*([^.;]+)")


@dataclass
class Task:
    task_id: str
    title: str
    completed: bool
    status: str


def read_tasks(path: Path) -> dict[str, Task]:
    tasks: dict[str, Task] = {}
    with path.open(encoding="utf-8") as task_file:
        for line in task_file:
            match = TASK_LINE.match(line)
            if not match:
                continue

            task_id = match.group("task_id")
            title = (match.group("title") or "").strip()
            status_match = STATUS.search(line)
            task = Task(
                task_id=task_id,
                title=title,
                completed=match.group("checked").lower() == "x",
                status=status_match.group(1).strip() if status_match else "",
            )

            existing = tasks.get(task_id)
            if existing is None:
                tasks[task_id] = task
                continue

            tasks[task_id] = Task(
                task_id=task_id,
                title=existing.title or task.title,
                completed=existing.completed or task.completed,
                status=existing.status or task.status,
            )
    return tasks


def read_queue(path: Path) -> list[tuple[str, str]]:
    queue: list[tuple[str, str]] = []
    with path.open(encoding="utf-8") as task_file:
        for line in task_file:
            match = QUEUE_LINE.match(line)
            if match:
                queue.append((match.group(1), match.group(2).strip()))
    return queue


def main() -> int:
    repository = Path(__file__).resolve().parents[1]
    backlog_path = repository / "docs" / "reference" / "backlog.md"
    completed_path = repository / "docs" / "history" / "completed-tasks.md"
    queue_path = repository / "TASK.md"

    try:
        tasks = read_tasks(backlog_path)
        for task_id, task in read_tasks(completed_path).items():
            existing = tasks.get(task_id)
            tasks[task_id] = Task(
                task_id=task_id,
                title=(existing.title if existing else "") or task.title,
                completed=(existing.completed if existing else False) or task.completed,
                status=(existing.status if existing else "") or task.status,
            )
        queue = read_queue(queue_path)
    except OSError as error:
        print(f"Error al leer los archivos de tareas: {error}", file=sys.stderr)
        return 1

    if not tasks:
        print("No se encontraron tareas en el backlog.", file=sys.stderr)
        return 1

    completed_count = sum(task.completed for task in tasks.values())
    total_count = len(tasks)
    percentage = completed_count / total_count * 100

    print("Avance del proyecto")
    print(f"Tareas completadas: {completed_count}/{total_count} ({percentage:.1f}%)")

    current_task = next(
        (tasks[task_id] for task_id, _ in queue
         if task_id in tasks and not tasks[task_id].completed),
        None,
    )
    if current_task is None:
        print("Tarea actual: no hay tareas pendientes en la cola de entrega.")
        return 0

    title = current_task.title or next(
        (queue_title for task_id, queue_title in queue if task_id == current_task.task_id),
        "",
    )
    print(f"Tarea actual: {current_task.task_id} - {title}")
    print(f"Estado: {current_task.status or 'Pendiente'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
