"""
Cleaner Agent — entropy management.

Harness Principle: Code entropy accumulates. The cleaner scans completed
work for deviations from golden principles and produces a targeted fix list.
"""
import json
from typing import Callable
import anthropic

from ..harness.context_engine import ContextEngine
from ..harness.entropy import EntropyTracker
from ..harness.feedback import extract_json_from_text
from ..tasks.queue import list_projects
from .base import call_agent

_ctx = ContextEngine()
_tracker = EntropyTracker()


def _build_outputs_summary(project_id: str | None = None) -> str:
    projects = list_projects()
    if project_id:
        projects = [p for p in projects if p.id == project_id]

    lines: list[str] = []
    for project in projects[:5]:
        lines.append(f"## Project {project.id}: {project.description}\n")
        for task in project.completed_tasks()[:4]:
            if task.output:
                preview = task.output[:600] + ("..." if len(task.output) > 600 else "")
                lines.append(f"### Task: {task.description}\n```\n{preview}\n```\n")

    return "\n".join(lines) or "No completed work to review."


async def run_entropy_cleanup(
    client: anthropic.AsyncAnthropic,
    project_id: str | None = None,
    stream_callback: Callable[[str], None] | None = None,
) -> dict:
    """
    Scans completed project outputs for entropy.
    Records score in EntropyTracker and returns the cleanup report.
    """
    summary = _build_outputs_summary(project_id)
    system_prompt = _ctx.for_cleaner(summary)

    raw = await call_agent(
        client,
        system_prompt,
        "Analyze all completed work. Identify every deviation from the golden principles.",
        use_thinking=False,
        stream_callback=stream_callback,
    )

    json_str = extract_json_from_text(raw)
    try:
        report = json.loads(json_str)
    except Exception:
        report = {"entropy_score": 5, "deviations": [], "summary": raw[:500]}

    _tracker.record(
        project_id or "global",
        report.get("entropy_score", 5),
        report.get("deviations", []),
    )
    return report
