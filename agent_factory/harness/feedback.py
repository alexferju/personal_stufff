"""
Feedback Loops & Self-Repair

Harness Principle: Help agents self-verify their work. Models are biased
toward their first plausible solution — prompt them aggressively to verify
by running tests and refining until correct.
"""
import json
from typing import Any, Callable, Awaitable


async def verify_and_repair(
    generate: Callable[[str | None], Awaitable[str]],
    verify: Callable[[str], tuple[bool, str]],
    max_attempts: int = 3,
) -> tuple[str, list[str]]:
    """
    Calls generate(), verifies with verify(), and retries on failure.

    generate(error_hint) -> output string
    verify(output) -> (ok: bool, error_msg: str)

    Returns (final_output, repair_history).
    """
    repair_history: list[str] = []
    last_output = ""
    last_error: str | None = None

    for attempt in range(max_attempts):
        last_output = await generate(last_error)
        ok, error_msg = verify(last_output)
        if ok:
            return last_output, repair_history
        repair_history.append(f"Attempt {attempt + 1} failed: {error_msg}")
        last_error = error_msg

    return last_output, repair_history


def verify_json_object(output: str, required_keys: list[str] | None = None) -> tuple[bool, str]:
    """Verifies output is valid JSON object with required keys."""
    # Strip markdown fences if present
    text = output.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            return False, "Output must be a JSON object, got array or scalar"
        if required_keys:
            missing = [k for k in required_keys if k not in data]
            if missing:
                return False, f"Missing required keys: {missing}"
        return True, ""
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"


def verify_task_list(output: str) -> tuple[bool, str]:
    """Verifies output is a valid JSON array of tasks."""
    text = output.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
    try:
        tasks = json.loads(text)
        if not isinstance(tasks, list):
            return False, "Output must be a JSON array"
        if not tasks:
            return False, "Task list is empty"
        required = ["id", "type", "description", "success_criterion"]
        for i, task in enumerate(tasks):
            missing = [k for k in required if k not in task]
            if missing:
                return False, f"Task {i} missing fields: {missing}"
        return True, ""
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"


def verify_review_output(output: str) -> tuple[bool, str]:
    return verify_json_object(output, required_keys=["verdict", "score", "summary"])


def verify_code_output(output: str) -> tuple[bool, str]:
    if len(output.strip()) < 30:
        return False, "Output too short to be valid code"
    return True, ""


def extract_json_from_text(text: str) -> str:
    """Extract first JSON object or array from free text."""
    import re
    # Try object first
    m = re.search(r'\{[\s\S]*\}', text)
    if m:
        return m.group(0)
    # Try array
    m = re.search(r'\[[\s\S]*\]', text)
    if m:
        return m.group(0)
    return text
