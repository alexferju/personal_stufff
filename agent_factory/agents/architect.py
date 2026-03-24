"""
Architect Agent — decomposes projects into atomic tasks.

Uses adaptive thinking for complex multi-step reasoning.
Harness: depth-first decomposition, layer ordering, self-repair loop.
"""
import json
from typing import Callable
import anthropic

from ..harness.context_engine import ContextEngine
from ..harness.feedback import verify_task_list, extract_json_from_text
from ..harness.constraints import validate_layer_order
from ..tasks.models import Task, TaskStatus

_ctx = ContextEngine()


async def decompose_project(
    client: anthropic.AsyncAnthropic,
    project_description: str,
    stream_callback: Callable[[str], None] | None = None,
) -> list[Task]:
    """
    Decomposes a project description into atomic Task objects.

    Self-repair loop: if the architect produces invalid JSON, it retries
    with the error fed back as context (up to 3 attempts).
    """
    system_prompt = _ctx.for_architect(project_description)
    base_message = (
        f"Decompose this project into atomic tasks:\n\n{project_description}\n\n"
        "Output ONLY the JSON array. No text before or after."
    )

    last_error: str | None = None

    for attempt in range(3):
        user_message = base_message
        if last_error:
            user_message += f"\n\nSELF-REPAIR: Previous output was invalid — {last_error}\nFix it and output valid JSON only."

        from .base import call_agent
        raw = await call_agent(
            client,
            system_prompt,
            user_message,
            use_thinking=True,
            stream_callback=stream_callback,
        )

        json_str = extract_json_from_text(raw)
        ok, error = verify_task_list(json_str)

        if ok:
            raw_tasks = json.loads(json_str)

            # Validate layer ordering, warn but don't block
            violations = validate_layer_order(raw_tasks)
            if violations and stream_callback:
                stream_callback(f"\n⚠  Layer order warnings: {[v.description for v in violations]}\n")

            return [
                Task(
                    id=t.get("id", f"task-{i+1:03d}"),
                    type=t.get("type", "code"),
                    layer=t.get("layer", "domain"),
                    description=t.get("description", ""),
                    success_criterion=t.get("success_criterion", ""),
                    depends_on=t.get("depends_on", []),
                    context=t.get("context", ""),
                    status=TaskStatus.PENDING.value,
                )
                for i, t in enumerate(raw_tasks)
            ]

        last_error = error
        if stream_callback:
            stream_callback(f"\n⚠  Architect attempt {attempt + 1} invalid ({error}), repairing...\n")

    # Fallback: single task wrapping the full description
    if stream_callback:
        stream_callback("\n⚠  Decomposition failed after 3 attempts. Falling back to single task.\n")
    return [Task(
        id="task-001",
        type="code",
        layer="domain",
        description=project_description,
        success_criterion="Complete working implementation delivered",
    )]
