"""
Coder Agent — writes clean, production-quality code.

Harness: layer-constrained system prompt, self-repair on review failure.
"""
from typing import Callable
import anthropic

from ..harness.context_engine import ContextEngine
from ..harness.feedback import verify_code_output
from ..tasks.models import Task
from .base import call_agent

_ctx = ContextEngine()


async def write_code(
    client: anthropic.AsyncAnthropic,
    task: Task,
    project_context: str = "",
    stream_callback: Callable[[str], None] | None = None,
) -> str:
    """
    Writes code for a given task with a self-repair loop.
    Returns the final code output string.
    """
    system_prompt = _ctx.for_coder(
        {
            "description": task.description,
            "success_criterion": task.success_criterion,
            "layer": task.layer,
            "context": task.context,
        },
        project_context,
    )

    last_error: str | None = None

    for attempt in range(3):
        user_message = f"Implement:\n{task.description}\n\nSuccess criterion: {task.success_criterion}"
        if last_error:
            user_message += f"\n\nSELF-REPAIR: Previous output failed verification — {last_error}\nProvide complete, correct code."

        output = await call_agent(
            client,
            system_prompt,
            user_message,
            use_thinking=False,
            stream_callback=stream_callback,
        )

        ok, error = verify_code_output(output)
        if ok:
            return output
        last_error = error

    return output
