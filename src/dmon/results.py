from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Union


CommandSnapshot = Union[str, Tuple[str, ...]]


@dataclass(frozen=True)
class TaskSnapshot:
    """Immutable snapshot of one recorded task process."""

    task: str
    pid: int
    status: str
    command: CommandSnapshot
    working_directory: str
    create_time: float
    create_time_human: str
    meta_path: str
    log_rotate: bool
    log_path: str
    rotate_log_path: str
    log_max_size: float
    log_backup_count: Optional[int]
    rotate_log_max_size: float
    rotate_log_backup_count: Optional[int]
    live_descendant_pids: Tuple[int, ...] = ()

    @property
    def running(self) -> bool:
        """Whether the snapshot reports the task as running."""
        return self.status == "running"


@dataclass(frozen=True)
class StackSnapshot:
    """Immutable snapshot of one recorded supervised stack."""

    stack: str
    status: str
    mode: str
    supervisor_pid: int
    supervisor_create_time: float
    state: str
    running_tasks: int
    total_tasks: int
    abort_on_exit: bool
    config_path: str
    log_path: str
    error: str
    tasks: Tuple[TaskSnapshot, ...]

    @property
    def exit_policy(self) -> str:
        """Return the stack's configured runtime exit policy."""
        return "abort-on-exit" if self.abort_on_exit else "keep-running"

    @property
    def running(self) -> bool:
        """Whether the snapshot reports the stack as running."""
        return self.status == "running"


@dataclass(frozen=True)
class TaskResult:
    """Result of inspecting one task, with a snapshot on success."""

    name: str
    snapshot: Optional[TaskSnapshot] = None
    error: str = ""

    @property
    def ok(self) -> bool:
        """Whether inspection produced a valid snapshot without an error."""
        return self.snapshot is not None and not self.error


@dataclass(frozen=True)
class StackResult:
    """Result of inspecting one stack, with a snapshot on success."""

    name: str
    snapshot: Optional[StackSnapshot] = None
    error: str = ""

    @property
    def ok(self) -> bool:
        """Whether inspection produced a valid snapshot without an error."""
        return self.snapshot is not None and not self.error


@dataclass(frozen=True)
class ActionResult:
    """Result of one task lifecycle action within a batch."""

    action: str
    name: str
    ok: bool
    exit_code: int
    snapshot: Optional[TaskSnapshot] = None
    error: str = ""


@dataclass(frozen=True)
class BatchResult:
    """Aggregate result for a multi-task lifecycle action."""

    action: str
    results: Tuple[ActionResult, ...]

    @property
    def ok(self) -> bool:
        """Whether every action in the batch succeeded."""
        return all(result.ok for result in self.results)

    @property
    def exit_code(self) -> int:
        """Return zero for a fully successful batch, otherwise one."""
        return 0 if self.ok else 1


@dataclass(frozen=True)
class WaitResult:
    """Finite readiness result for one configured task."""

    target: str
    ready: bool
    reason: str
    elapsed: float
    attempts: int
    error: str = ""
