"""Shared text helpers for model responses."""

import json


def content_to_text(content: object) -> str:
    """Return a string representation of a LangChain message content value."""

    return content if isinstance(content, str) else str(content)


def extract_json_object(text: str) -> str:
    """Return the first balanced valid JSON object embedded in ``text``."""

    stripped = text.strip()
    if _is_json_object(stripped):
        return stripped
    for start_index, character in enumerate(stripped):
        if character != "{":
            continue
        candidate = _balanced_candidate(stripped, start_index)
        if candidate is not None and _is_json_object(candidate):
            return candidate
    return stripped


def _is_json_object(text: str) -> bool:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return False
    return isinstance(payload, dict)


def _balanced_candidate(text: str, start_index: int) -> str | None:
    depth = 0
    in_string = False
    escaped = False
    for index in range(start_index, len(text)):
        character = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return text[start_index : index + 1]
    return None
