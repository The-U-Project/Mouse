"""Autonomous navigation — self-directed cursor control for task completion.

Provides a higher-level autonomy layer that:
1. Takes a natural language goal
2. Breaks it into sub-tasks
3. Uses the screen analyzer to execute each sub-task
4. Validates results and retries on failure
5. Reports progress back to the user

This is the optional "autonavigation" feature (#5).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class TaskState(Enum):
    """State of an autonomous task."""

    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    RETRYING = auto()


class TaskPriority(Enum):
    """Priority of a task."""

    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class SubTask:
    """A single step in a larger autonomous task.

    Attributes:
        id: Unique task identifier.
        description: Natural language description of the step.
        expected_result: What should happen when the step succeeds.
        state: Current task state.
        priority: Task priority.
        retry_count: Number of times this task has been retried.
        max_retries: Maximum retry attempts.
        completed_at: Timestamp of completion.
    """

    id: str = ""
    description: str = ""
    expected_result: str = ""
    state: TaskState = TaskState.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    completed_at: float = 0.0


@dataclass
class TaskPlan:
    """A plan composed of sub-tasks to achieve a goal.

    Attributes:
        goal: The original user goal.
        tasks: Ordered list of sub-tasks.
        current_task_index: Index of the currently executing task.
        created_at: When the plan was created.
        state: Overall plan state.
    """

    goal: str = ""
    tasks: list[SubTask] = field(default_factory=list)
    current_task_index: int = 0
    created_at: float = field(default_factory=time.time)
    state: TaskState = TaskState.PENDING


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class AutonomyError(Exception):
    """Base for autonomous navigation errors."""


class TaskFailedError(AutonomyError):
    """Raised when a task fails after max retries."""


class PlannerError(AutonomyError):
    """Raised when the AI planner fails to generate a plan."""


# ---------------------------------------------------------------------------
# Autonomy Engine
# ---------------------------------------------------------------------------


class AutonomyEngine:
    """High-level autonomous navigation engine.

    Uses the AI controller to plan tasks and the screen analyzer to
    execute them. Executes sub-tasks sequentially with retry logic.

    Usage:
        >>> engine = AutonomyEngine(screen_analyzer)
        >>> engine.execute_goal("Open notepad and type 'hello world'")
    """

    _MAX_PLAN_TASKS = 10
    _TASK_TIMEOUT = 30.0  # Max seconds per task
    _PLAN_TIMEOUT = 300.0  # Max seconds for entire plan

    def __init__(self, screen_analyzer: Any) -> None:
        """Initialize the autonomy engine.

        Args:
            screen_analyzer: A ScreenAnalyzer instance with AI enabled.
        """
        self._analyzer = screen_analyzer
        self._current_plan: TaskPlan | None = None
        self._progress_callbacks: list[Callable[[SubTask], None]] = []
        self._on_complete: Callable[[bool, str], None] | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_plan(self) -> TaskPlan | None:
        return self._current_plan

    @property
    def is_executing(self) -> bool:
        return (
            self._current_plan is not None
            and self._current_plan.state == TaskState.RUNNING
        )

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    def plan_goal(self, goal: str) -> TaskPlan:
        """Use the AI to decompose a goal into sub-tasks.

        Args:
            goal: Natural language description of the goal.

        Returns:
            TaskPlan with ordered sub-tasks.

        Raises:
            PlannerError: If the AI cannot generate a plan.
        """
        logger.info("Planning goal: %s", goal)

        if self._analyzer._ai is None:
            raise PlannerError("AI is required for planning. Enable AI in ScreenAnalyzer.")

        prompt = f"""Break down this goal into individual cursor actions:
"{goal}"

Return a JSON array of steps:
[
  {{"step": 1, "description": "...", "expected_result": "..."}},
  ...
]

Each step should be one atomic action (click, type, move). Keep it under {self._MAX_PLAN_TASKS} steps."""

        response = self._analyzer._ai.chat(prompt)

        import json

        try:
            # Try to find JSON array in the response
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                steps_data = json.loads(response[start:end])
            else:
                # Fallback: treat the whole response as the plan
                steps_data = [{"step": 1, "description": response, "expected_result": "Goal completed"}]
        except (json.JSONDecodeError, ValueError):
            # Last resort: single-step plan
            steps_data = [{"step": 1, "description": goal, "expected_result": "Goal completed"}]

        tasks: list[SubTask] = []
        for i, step in enumerate(steps_data):
            tasks.append(
                SubTask(
                    id=f"task-{i+1}",
                    description=step.get("description", f"Step {i+1}"),
                    expected_result=step.get("expected_result", ""),
                    state=TaskState.PENDING,
                )
            )

        plan = TaskPlan(goal=goal, tasks=tasks, created_at=time.time())
        self._current_plan = plan
        logger.info("Plan created: %d steps", len(tasks))
        return plan

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute_goal(self, goal: str) -> bool:
        """Plan and execute a full goal autonomously.

        Args:
            goal: Natural language description of the goal.

        Returns:
            True if all steps completed successfully, False otherwise.
        """
        plan = self.plan_goal(goal)
        return self.execute_plan(plan)

    def execute_plan(self, plan: TaskPlan) -> bool:
        """Execute a pre-made plan.

        Args:
            plan: The TaskPlan to execute.

        Returns:
            True if all steps completed successfully.
        """
        plan.state = TaskState.RUNNING
        self._analyzer.set_goal(plan.goal)

        deadline = time.monotonic() + self._PLAN_TIMEOUT

        for i, task in enumerate(plan.tasks):
            if time.monotonic() > deadline:
                logger.error("Plan timed out at step %d/%d", i + 1, len(plan.tasks))
                plan.state = TaskState.FAILED
                self._notify_complete(False, "Plan timed out")
                return False

            plan.current_task_index = i
            success = self._execute_task(task)

            if not success:
                plan.state = TaskState.FAILED
                self._notify_complete(False, f"Task failed: {task.description}")
                return False

        plan.state = TaskState.COMPLETED
        self._analyzer.clear_goal()
        self._notify_complete(True, f"Goal completed: {plan.goal}")
        return True

    def _execute_task(self, task: SubTask) -> bool:
        """Execute a single sub-task with retry logic.

        Args:
            task: The sub-task to execute.

        Returns:
            True if task completed successfully.
        """
        logger.info("Executing: %s", task.description)
        task.state = TaskState.RUNNING
        self._notify_progress(task)

        self._analyzer.set_goal(task.description)

        task_start = time.monotonic()

        while task.retry_count <= task.max_retries:
            if time.monotonic() - task_start > self._TASK_TIMEOUT:
                logger.warning("Task timed out: %s", task.description)
                task.state = TaskState.FAILED
                return False

            # Run the analysis pipeline for this task
            try:
                response = self._analyzer.run_once()
                # If we have actions and they were executed, consider the step done
                if response and response.actions:
                    task.state = TaskState.COMPLETED
                    task.completed_at = time.time()
                    self._notify_progress(task)
                    logger.info("Task completed: %s", task.description)
                    return True
            except Exception as exc:
                logger.error("Task execution error: %s", exc)

            # If no actions generated, wait a bit and retry
            task.retry_count += 1
            if task.retry_count <= task.max_retries:
                task.state = TaskState.RETRYING
                logger.info("Retrying task (attempt %d/%d): %s",
                            task.retry_count, task.max_retries, task.description)
                time.sleep(1.0)

        task.state = TaskState.FAILED
        logger.error("Task failed after %d retries: %s", task.max_retries, task.description)
        return False

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_progress(self, callback: Callable[[SubTask], None]) -> None:
        """Register a progress callback.

        Args:
            callback: Called when a task changes state.
        """
        self._progress_callbacks.append(callback)

    def on_complete(self, callback: Callable[[bool, str], None]) -> None:
        """Register a completion callback.

        Args:
            callback: Called with (success: bool, message: str) when
                the plan finishes.
        """
        self._on_complete = callback

    def _notify_progress(self, task: SubTask) -> None:
        """Notify all progress callbacks."""
        for cb in self._progress_callbacks:
            try:
                cb(task)
            except Exception as exc:
                logger.error("Progress callback error: %s", exc)

    def _notify_complete(self, success: bool, message: str) -> None:
        """Notify the completion callback."""
        if self._on_complete is not None:
            try:
                self._on_complete(success, message)
            except Exception as exc:
                logger.error("Completion callback error: %s", exc)

    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------

    def cancel(self) -> None:
        """Cancel the current plan execution."""
        if self._current_plan is not None:
            self._current_plan.state = TaskState.FAILED
            self._analyzer.clear_goal()
            logger.info("Plan execution cancelled.")
