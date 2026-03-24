"""Task and Project data models — the types layer of The Agent Factory."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TaskType(str, Enum):
    CODE = "code"
    REVIEW = "review"
    TEST = "test"
    CLEANUP = "cleanup"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProjectStatus(str, Enum):
    PENDING = "pending"
    DECOMPOSING = "decomposing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STEERED = "steered"


@dataclass
class Task:
    id: str
    type: str
    layer: str
    description: str
    success_criterion: str
    depends_on: list[str] = field(default_factory=list)
    context: str = ""
    status: str = TaskStatus.PENDING.value
    output: str = ""
    review: Optional[dict] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    error: Optional[str] = None


@dataclass
class SteeringEntry:
    timestamp: str
    direction: str


@dataclass
class Project:
    id: str
    description: str
    status: str = ProjectStatus.PENDING.value
    tasks: list[Task] = field(default_factory=list)
    outputs: dict = field(default_factory=dict)
    steering_history: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    error: Optional[str] = None

    def get_task(self, task_id: str) -> Optional[Task]:
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None

    def tasks_by_status(self, status: str) -> list[Task]:
        return [t for t in self.tasks if t.status == status]

    def pending_tasks(self) -> list[Task]:
        return self.tasks_by_status(TaskStatus.PENDING.value)

    def completed_tasks(self) -> list[Task]:
        return self.tasks_by_status(TaskStatus.COMPLETED.value)

    def are_dependencies_met(self, task: Task) -> bool:
        completed_ids = {t.id for t in self.completed_tasks()}
        return all(dep in completed_ids for dep in task.depends_on)

    def ready_tasks(self) -> list[Task]:
        return [t for t in self.pending_tasks() if self.are_dependencies_met(t)]
