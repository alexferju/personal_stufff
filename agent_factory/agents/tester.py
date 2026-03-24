"""
Tester Agent — writes comprehensive tests that verify code correctness.
"""
from typing import Callable
import anthropic

from ..harness.context_engine import ContextEngine
from ..tasks.models import Task
from .base import call_agent

_ctx = ContextEngine()


async def write_tests(
    client: anthropic.AsyncAnthropic,
    task: Task,
    code: str,
    stream_callback: Callable[[str], None] | None = None,
) -> str:
    """
    Writes a pytest test file for the given code.
    Returns the complete test file as a string.
    """
    system_prompt = _ctx.for_tester(
        {"description": task.description, "success_criterion": task.success_criterion},
        code,
    )

    return await call_agent(
        client,
        system_prompt,
        f"Write comprehensive tests for: {task.description}",
        use_thinking=False,
        stream_callback=stream_callback,
    )
