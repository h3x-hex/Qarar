"""Provider-agnostic LLM abstraction with lazy optional imports."""

from __future__ import annotations

import json
import os
from typing import Any

ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
OPENAI_MODEL = "gpt-4o-mini"


class LLMUnavailable(Exception):
    """Raised when no LLM provider/key is available."""


def _provider() -> str:
    return os.environ.get("LLM_PROVIDER", "none").lower().strip()


def _model() -> str:
    explicit = os.environ.get("LLM_MODEL")
    if explicit:
        return explicit
    if _provider() == "anthropic":
        return ANTHROPIC_MODEL
    if _provider() == "openai":
        return OPENAI_MODEL
    return ""


def is_llm_available() -> bool:
    try:
        _ensure_available()
        return True
    except LLMUnavailable:
        return False


def _ensure_available() -> None:
    provider = _provider()
    if provider in ("", "none"):
        raise LLMUnavailable("LLM_PROVIDER is none")
    if provider == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise LLMUnavailable("ANTHROPIC_API_KEY not set")
        return
    if provider == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            raise LLMUnavailable("OPENAI_API_KEY not set")
        return
    raise LLMUnavailable(f"Unknown LLM_PROVIDER: {provider}")


def _anthropic_tools(tools: list[dict]) -> list[dict]:
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["parameters"],
        }
        for t in tools
    ]


def _openai_tools(tools: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in tools
    ]


def _parse_anthropic_response(response: Any) -> dict[str, Any]:
    text_parts: list[str] = []
    tool_calls: list[dict] = []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append(
                {"id": block.id, "name": block.name, "arguments": block.input}
            )
    return {"text": "\n".join(text_parts) if text_parts else None, "tool_calls": tool_calls}


def _parse_openai_response(message: Any) -> dict[str, Any]:
    text = message.content
    tool_calls: list[dict] = []
    if message.tool_calls:
        for tc in message.tool_calls:
            args = tc.function.arguments
            if isinstance(args, str):
                args = json.loads(args)
            tool_calls.append(
                {"id": tc.id, "name": tc.function.name, "arguments": args}
            )
    return {"text": text, "tool_calls": tool_calls}


def complete_with_tools(messages: list[dict], tools: list[dict]) -> dict[str, Any]:
    """Call LLM with tool schemas. Returns {text, tool_calls}."""
    _ensure_available()
    provider = _provider()
    model = _model()

    try:
        if provider == "anthropic":
            import anthropic

            client = anthropic.Anthropic()
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=next((m["content"] for m in messages if m["role"] == "system"), ""),
                messages=[m for m in messages if m["role"] != "system"],
                tools=_anthropic_tools(tools),
            )
            return _parse_anthropic_response(response)

        if provider == "openai":
            from openai import OpenAI

            client = OpenAI()
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=_openai_tools(tools),
                tool_choice="auto",
            )
            return _parse_openai_response(response.choices[0].message)

        raise LLMUnavailable(f"Unknown provider: {provider}")
    except LLMUnavailable:
        raise
    except Exception as exc:
        raise LLMUnavailable(str(exc)) from exc
