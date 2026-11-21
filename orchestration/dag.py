"""A tiny, dependency-aware DAG runner.

This is a deliberately small stand-in for Airflow / Prefect: it models the
pipeline as tasks with dependencies, runs them in topological order, logs
and times each one, retries on failure, and stops the run if a task fails.
The same task graph would map directly onto an Airflow DAG or a Prefect flow.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger("orchestration")

# A task reads from / writes to a shared run context (dict).
TaskFn = Callable[[dict], None]


@dataclass
class Task:
    name: str
    fn: TaskFn
    depends_on: list[str] = field(default_factory=list)
    retries: int = 0


class DAG:
    """Holds tasks and runs them in dependency order."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.tasks: dict[str, Task] = {}

    def add(self, task: Task) -> "DAG":
        if task.name in self.tasks:
            raise ValueError(f"Duplicate task '{task.name}'")
        self.tasks[task.name] = task
        return self

    def _topological_order(self) -> list[Task]:
        """Return tasks ordered so every dependency comes first (Kahn's algo)."""
        indegree = {n: 0 for n in self.tasks}
        dependents: dict[str, list[str]] = {n: [] for n in self.tasks}
        for name, task in self.tasks.items():
            for dep in task.depends_on:
                if dep not in self.tasks:
                    raise ValueError(f"Task '{name}' depends on unknown '{dep}'")
                indegree[name] += 1
                dependents[dep].append(name)

        ready = [n for n, d in indegree.items() if d == 0]
        order: list[str] = []
        while ready:
            n = ready.pop(0)
            order.append(n)
            for m in dependents[n]:
                indegree[m] -= 1
                if indegree[m] == 0:
                    ready.append(m)

        if len(order) != len(self.tasks):
            raise ValueError("Cycle detected in DAG")
        return [self.tasks[n] for n in order]

    def _run_task(self, task: Task, context: dict) -> None:
        attempts = task.retries + 1
        for attempt in range(1, attempts + 1):
            start = time.perf_counter()
            try:
                task.fn(context)
                elapsed = time.perf_counter() - start
                logger.info("OK    %-14s (%.2fs)", task.name, elapsed)
                return
            except Exception as exc:  # noqa: BLE001 - we log and maybe retry
                logger.warning(
                    "FAIL  %-14s attempt %d/%d: %s",
                    task.name,
                    attempt,
                    attempts,
                    exc,
                )
                if attempt == attempts:
                    raise

    def run(self, context: dict | None = None) -> dict:
        """Execute the DAG. Returns the final run context."""
        context = context if context is not None else {}
        logger.info("=== DAG '%s' started ===", self.name)
        for task in self._topological_order():
            self._run_task(task, context)
        logger.info("=== DAG '%s' finished ===", self.name)
        return context
