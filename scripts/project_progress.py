#!/usr/bin/env python3
"""Show task progress from the configured GitHub issue tracker."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

QUEUE_LINE = re.compile(r"^\|\s*\d+\s*\|\s*(T\d+)\s*\|")
ISSUE_TITLE = re.compile(r"^(T\d+)\s+-\s+(.*)$")


@dataclass
class Task:
    task_id: str
    title: str
    number: int
    state: str
    status: str


def find_gh() -> str | None:
    executable = shutil.which("gh")
    if executable:
        return executable

    if sys.platform == "win32":
        candidates = [
            Path("C:/Program Files/GitHub CLI/gh.exe"),
            Path.home() / "AppData/Local/Programs/GitHub CLI/gh.exe",
        ]
        return next((str(path) for path in candidates if path.is_file()), None)
    return None


def read_tracker_tasks(gh: str, repository: Path) -> dict[str, Task]:
    result = subprocess.run(
        [
            gh,
            "issue",
            "list",
            "--state",
            "all",
            "--limit",
            "500",
            "--label",
            "project-task",
            "--json",
            "number,title,state,labels",
        ],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    tasks: dict[str, Task] = {}
    for issue in json.loads(result.stdout):
        title_match = ISSUE_TITLE.match(issue["title"])
        if not title_match:
            continue

        task_id, title = title_match.groups()
        if task_id in tasks:
            raise ValueError(f"Multiple GitHub task issues use ID {task_id}.")

        labels = {label["name"] for label in issue["labels"]}
        status_label = next(
            (label.removeprefix("status:") for label in labels if label.startswith("status:")),
            "pending",
        )
        state = issue["state"].upper()
        if state == "CLOSED":
            status = "Cancelled" if status_label == "cancelled" else "Completed"
        else:
            status = {
                "pending": "Pending",
                "in-progress": "In progress",
                "blocked": "Blocked",
                "deferred": "Deferred",
            }.get(status_label, status_label.replace("-", " ").title())

        tasks[task_id] = Task(task_id, title, issue["number"], state, status)

    if not tasks:
        raise ValueError("No task issues with the `project-task` label were found.")
    return tasks


def read_queue(path: Path) -> list[str]:
    queue = []
    with path.open(encoding="utf-8") as task_file:
        for line in task_file:
            match = QUEUE_LINE.match(line)
            if match:
                queue.append(match.group(1))
    return queue


def main() -> int:
    repository = Path(__file__).resolve().parents[1]
    gh = find_gh()
    if gh is None:
        print("GitHub CLI (`gh`) is required and was not found.", file=sys.stderr)
        return 1

    try:
        tasks = read_tracker_tasks(gh, repository)
        queue = read_queue(repository / "tasks.md")
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        detail = getattr(error, "stderr", None) or str(error)
        print(f"Unable to read task progress from GitHub: {detail}", file=sys.stderr)
        return 1

    completed_count = sum(task.status == "Completed" for task in tasks.values())
    total_count = len(tasks)
    percentage = completed_count / total_count * 100

    print("Project progress (GitHub Issues)")
    print(f"Completed tasks: {completed_count}/{total_count} ({percentage:.1f}%)")

    current_task = next(
        (
            tasks[task_id]
            for task_id in queue
            if task_id in tasks
            and tasks[task_id].state != "CLOSED"
            and tasks[task_id].status != "Deferred"
        ),
        None,
    )
    if current_task is None:
        print("Current task: no pending task in the delivery queue.")
        return 0

    print(f"Current task: {current_task.task_id} - {current_task.title}")
    print(f"Status: {current_task.status}")
    print(f"GitHub issue: #{current_task.number}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
