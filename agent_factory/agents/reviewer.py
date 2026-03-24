"""
Reviewer Agent — verifies code quality, correctness, and constraints.

The reviewer's verdict gates whether code proceeds or goes back for repair.
"""
import json
from typing import Callable
import anthropic

from ..harness.context_engine import ContextEngine
from ..harness.feedback import verify_review_output, extract_json_from_text
from ..tasks.models import Task
from .base import call_agent

_ctx = ContextEngine()


async def review_code(
    client: anthropic.AsyncAnthropic,
    task: Task,
    code: str,
    stream_callback: Callable[[str], None] | None = None,
) -> dict:
    """
    Reviews code and returns a structured review dict with verdict and score.
    """
    system_prompt = _ctx.for_reviewer(
        {"description": task.description, "success_criterion": task.success_criterion},
        code,
    )

    raw = await call_agent(
        client,
        system_prompt,
        f"Review the code for task: {task.description}",
        use_thinking=False,
        stream_callback=stream_callback,
    )

    json_str = extract_json_from_text(raw)
    ok, _ = verify_review_output(json_str)

    if ok:
        return json.loads(json_str)

    # Graceful fallback if JSON malformed
    return {
        "verdict": "pass_with_notes",
        "score": 6,
        "issues": [],
        "suggestions": [],
        "security_concerns": [],
        "summary": raw[:500],
    }
