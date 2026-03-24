"""
Task Queue — persists projects and tasks to disk as JSON.

Simple, durable, no external dependencies.
"""
import json
from pathlib import Path
from dataclasses import asdict
from .models import Project, Task, TaskStatus, ProjectStatus

OUTPUTS_DIR = Path("outputs")


def _project_path(project_id: str) -> Path:
    return OUTPUTS_DIR / f"project_{project_id}.json"


def _serialize(obj) -> object:
    """Custom JSON serializer for dataclass fields."""
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    return obj


def save_project(project: Project):
    OUTPUTS_DIR.mkdir(exist_ok=True)
    data = asdict(project)
    _project_path(project.id).write_text(json.dumps(data, indent=2, default=str))


def load_project(project_id: str) -> Project | None:
    path = _project_path(project_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        raw_tasks = data.pop("tasks", [])
        project = Project(**data)
        project.tasks = [Task(**t) for t in raw_tasks]
        return project
    except Exception:
        return None


def list_projects() -> list[Project]:
    OUTPUTS_DIR.mkdir(exist_ok=True)
    projects = []
    for f in sorted(OUTPUTS_DIR.glob("project_*.json"),
                    key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text())
            raw_tasks = data.pop("tasks", [])
            p = Project(**data)
            p.tasks = [Task(**t) for t in raw_tasks]
            projects.append(p)
        except Exception:
            continue
    return projects


def update_task(project_id: str, task_id: str, **kwargs):
    """Convenience: load project, update task fields, save."""
    project = load_project(project_id)
    if not project:
        return
    task = project.get_task(task_id)
    if task:
        for key, val in kwargs.items():
            setattr(task, key, val)
    save_project(project)
