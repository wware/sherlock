#!/usr/bin/env python3
"""
Utilities for robust JSON extraction from LLM responses.
"""

from __future__ import annotations

import json
import re
from typing import Any

MAX_SNIPPET_LENGTH = 160


def _candidate_texts(raw_text: str) -> list[str]:
    text = raw_text.strip()
    candidates = [text] if text else []

    fenced = re.findall(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    candidates.extend(block.strip() for block in fenced if block.strip())
    return candidates


def _raw_decode_any(text: str) -> Any:
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch not in "{[":
            continue
        try:
            obj, _ = decoder.raw_decode(text[idx:])
            return obj
        except json.JSONDecodeError:
            continue
    snippet = text[:MAX_SNIPPET_LENGTH].replace("\n", "\\n")
    msg = f"No JSON object/array found in response snippet: {snippet!r}"
    raise json.JSONDecodeError(msg, text, 0)


def parse_llm_json(raw_text: str) -> Any:
    """Parse JSON from plain, fenced, or mixed-content LLM text responses."""
    last_error: Exception | None = None
    for candidate in _candidate_texts(raw_text):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
        try:
            return _raw_decode_any(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
    if last_error:
        raise last_error
    raise json.JSONDecodeError("No valid JSON found in response", raw_text, 0)


def anthropic_text(resp: Any) -> str:
    """Extract and concatenate text blocks from an Anthropic messages response."""
    parts = []
    for block in getattr(resp, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()
