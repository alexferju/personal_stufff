"""
Dispatcher — orchestrates agents to execute a full project pipeline.

Pipeline: Decompose → Code → Review → (Self-repair if fail) → Test
Harness: feedback loops, dependency ordering, entropy detection.
"""
import uuid
from datetime import datetime
from typing import Callable
import anthropic

from ..agents.architect import decompose_project
from ..agents.coder import write_code
from ..agents.reviewer import review_code
from ..agents.tester import write_tests
from ..tasks.models import Project, ProjectStatus, TaskStatus
from ..tasks.queue import save_project, load_project


async def run_project(
    project_id: str,
    project_description: str,
    stream_callback: Callable[[str], None] | None = None,
) -> Project:
    """
    Full autonomous pipeline for a project.

    1. Architect decomposes the project into tasks
    2. Ready tasks execute in dependency order
    3. Code tasks auto-trigger a Review
    4. Failed reviews trigger self-repair (re-code with feedback)
    5. Test tasks write pytest files
    """
    client = anthropic.AsyncAnthropic()

    def emit(msg: str):
        if stream_callback:
            stream_callback(msg)

    # --- Create & persist project ---
    project = Project(
        id=project_id,
        description=project_description,
        status=ProjectStatus.DECOMPOSING.value,
    )
    save_project(project)

    emit(f"\n{'━'*62}\n")
    emit(f"  THE AGENT FACTORY — Project {project_id}\n")
    emit(f"{'━'*62}\n\n")
    emit(f"[ARCHITECT] Decomposing project...\n\n")

    # --- Decompose ---
    tasks = await decompose_project(client, project_description, stream_callback=stream_callback)
    project.tasks = tasks
    project.status = ProjectStatus.RUNNING.value
    save_project(project)

    emit(f"\n\n✦ {len(tasks)} task(s) identified\n\n")

    # --- Execute in dependency order ---
    completed_outputs: dict[str, str] = {}
    max_rounds = len(tasks) * 3  # allow retries

    for _ in range(max_rounds):
        ready = project.ready_tasks()
        if not ready:
            if project.pending_tasks():
                emit("\n⚠  No ready tasks but pending tasks remain — possible dependency cycle\n")
            break

        for task in ready:
            emit(f"\n{'─'*62}\n")
            emit(f"[{task.type.upper()}] {task.id}  ·  layer:{task.layer}\n")
            emit(f"{task.description}\n")
            emit(f"{'─'*62}\n")

            task.status = TaskStatus.RUNNING.value
            save_project(project)

            # Build context from completed dependency outputs
            dep_context = ""
            for dep_id in task.depends_on:
                if dep_id in completed_outputs:
                    dep_context += f"\n## Output of {dep_id}:\n{completed_outputs[dep_id][:1200]}\n"

            try:
                if task.type == "code":
                    output = await write_code(
                        client, task,
                        project_context=dep_context,
                        stream_callback=stream_callback,
                    )
                    task.output = output

                    # Auto-review every code task
                    emit(f"\n\n[REVIEWER] Reviewing {task.id}...\n")
                    review = await review_code(
                        client, task, output,
                        stream_callback=stream_callback,
                    )
                    task.review = review
                    verdict = review.get("verdict", "pass")
                    score = review.get("score", 7)
                    emit(f"\n[REVIEW] verdict={verdict}  score={score}/10\n")

                    if verdict == "fail":
                        # Self-repair: feed review back as context and re-queue
                        emit(f"[SELF-REPAIR] Review failed — re-queuing with feedback\n")
                        issues = review.get("issues", [])
                        task.context += (
                            f"\n\nPrevious code failed review:\n"
                            f"Summary: {review.get('summary', '')}\n"
                            f"Issues: {issues}"
                        )
                        task.status = TaskStatus.PENDING.value
                        task.output = ""
                    else:
                        task.status = TaskStatus.COMPLETED.value
                        completed_outputs[task.id] = output

                elif task.type == "test":
                    dep_code = completed_outputs.get(task.depends_on[0], "") if task.depends_on else ""
                    output = await write_tests(
                        client, task, dep_code,
                        stream_callback=stream_callback,
                    )
                    task.output = output
                    task.status = TaskStatus.COMPLETED.value
                    completed_outputs[task.id] = output

                else:
                    # review/cleanup tasks treated as code tasks
                    output = await write_code(
                        client, task,
                        project_context=dep_context,
                        stream_callback=stream_callback,
                    )
                    task.output = output
                    task.status = TaskStatus.COMPLETED.value
                    completed_outputs[task.id] = output

                if task.status == TaskStatus.COMPLETED.value:
                    task.completed_at = datetime.utcnow().isoformat()
                    emit(f"\n✓ {task.id} completed\n")

            except Exception as exc:
                task.status = TaskStatus.FAILED.value
                task.error = str(exc)
                emit(f"\n✗ {task.id} failed: {exc}\n")

            save_project(project)

        if not project.pending_tasks():
            break

    project.status = ProjectStatus.COMPLETED.value
    project.completed_at = datetime.utcnow().isoformat()
    save_project(project)

    completed = len(project.completed_tasks())
    total = len(project.tasks)
    emit(f"\n{'━'*62}\n")
    emit(f"  PROJECT COMPLETE  ·  {completed}/{total} tasks done\n")
    emit(f"  ID: {project_id}\n")
    emit(f"{'━'*62}\n")

    return project
