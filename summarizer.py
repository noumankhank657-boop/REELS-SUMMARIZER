"""Extract only actionable sales and hook notes from a reel transcript."""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

SCHEMA_VERSION = 3
REQUIRED_FIELDS = {"use_when", "content_ideas", "hook_mechanics", "hook_pattern", "sales_advice"}


def summarize_transcript(transcript: str) -> dict[str, Any]:
    """Ask DeepSeek for exactly the five requested fields."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is missing. Add it to your .env file.")
    if not transcript.strip():
        raise ValueError("The transcript is empty.")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract only concise, useful information for sales and content "
                    "creation. Do not add a title, purpose, summary, topic, source link, "
                    "transcript, or any other fields. Do not invent claims or advice. "
                    "Return one JSON object with exactly these keys: use_when (one short "
                    "sentence describing the situation where this advice applies; use "
                    "'Not specified in the reel' if absent), content_ideas (1 or 2 short "
                    "ideas directly adapted from the reel), hook_mechanics (one short "
                    "explanation of how the hook holds attention; if interpreting, say "
                    "so; use 'Not covered' if no hook is present), hook_pattern (brief "
                    "reusable structure of the actual hook, or 'Not covered'), sales_advice "
                    "(1 to 3 concise actionable points actually supported by the speaker). "
                    "Keep every value short. Use lists of strings for content_ideas and "
                    "sales_advice. Do not include any text outside the JSON object."
                ),
            },
            {"role": "user", "content": transcript},
        ],
    )

    message = response.choices[0].message.content
    if not message:
        raise ValueError("DeepSeek returned an empty response.")
    try:
        result = json.loads(message)
    except json.JSONDecodeError as exc:
        raise ValueError("DeepSeek did not return valid JSON.") from exc

    if not isinstance(result, dict):
        raise ValueError("DeepSeek response must be a JSON object.")
    missing = REQUIRED_FIELDS - result.keys()
    if missing:
        raise ValueError(f"DeepSeek response is missing fields: {', '.join(sorted(missing))}")
    extra = result.keys() - REQUIRED_FIELDS
    if extra:
        raise ValueError(f"DeepSeek returned unrequested fields: {', '.join(sorted(extra))}")
    for field in ("use_when", "hook_mechanics", "hook_pattern"):
        if not isinstance(result[field], str):
            raise ValueError(f"DeepSeek field '{field}' must be text.")
    for field in ("content_ideas", "sales_advice"):
        if not isinstance(result[field], list) or not all(
            isinstance(item, str) for item in result[field]
        ):
            raise ValueError(f"DeepSeek field '{field}' must be a list of text items.")
    return result
