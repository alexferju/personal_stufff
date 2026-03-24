"""
Base Agent — wraps a model call with the harness.

Agent = Model + Harness.
The model contains the intelligence. This module makes it useful.
"""
import anthropic
from typing import Callable, Awaitable


async def call_agent(
    client: anthropic.AsyncAnthropic,
    system_prompt: str,
    user_message: str,
    use_thinking: bool = False,
    stream_callback: Callable[[str], None] | None = None,
) -> str:
    """
    Core agent call. Streams output and returns final text.

    Uses claude-opus-4-6 with adaptive thinking for complex tasks.
    Streams all output to stream_callback if provided.
    """
    kwargs: dict = {
        "model": "claude-opus-4-6",
        "max_tokens": 16000,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
    }

    if use_thinking:
        kwargs["thinking"] = {"type": "adaptive"}

    chunks: list[str] = []

    async with client.messages.stream(**kwargs) as stream:
        async for event in stream:
            if event.type == "content_block_delta":
                delta = event.delta
                if hasattr(delta, "text"):
                    chunks.append(delta.text)
                    if stream_callback:
                        stream_callback(delta.text)

    return "".join(chunks)
