"""Roster-photo import: turn an image of a name list into extracted player names.

Uses the Anthropic vision model with structured JSON output, mirroring the
error-handling pattern in routers/insights.py.
"""

import json

import anthropic
from fastapi import HTTPException, status

from app.config import settings

# Reuse the model the rest of the app already relies on so it's guaranteed to be
# available on the configured API key. A cheaper vision-capable model (e.g. a
# Sonnet/Haiku tier) can be swapped in here to cut per-import cost.
_VISION_MODEL = "claude-opus-4-8"
_MAX_NAMES = 200

_ROSTER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["names"],
    "properties": {
        "names": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Each distinct person's name found in the image, in the order shown",
        }
    },
}

_SYSTEM_PROMPT = (
    "You extract player/person names from an image of a team roster or name list. "
    "Return every distinct person's name you can read, in the order they appear. "
    "For each entry return ONLY the person's name — strip row numbers, jersey "
    "numbers, positions, skill levels, dates, phone numbers, emails, and column "
    "headers. If the image contains no readable names, return an empty list. Never "
    "invent names that are not visible in the image."
)


def extract_roster_names(image_base64: str, media_type: str) -> list[str]:
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Photo import is not configured yet — add ANTHROPIC_API_KEY to backend/.env",
        )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        response = client.messages.create(
            model=_VISION_MODEL,
            max_tokens=2000,
            system=_SYSTEM_PROMPT,
            output_config={"format": {"type": "json_schema", "schema": _ROSTER_SCHEMA}},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_base64,
                            },
                        },
                        {"type": "text", "text": "Extract the names from this roster image."},
                    ],
                }
            ],
        )
    except anthropic.AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The configured Anthropic API key was rejected",
        ) from exc
    except anthropic.RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is rate-limited right now — try again in a moment",
        ) from exc
    except anthropic.APIStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error ({exc.status_code})",
        ) from exc
    except anthropic.APIConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the AI service",
        ) from exc

    if response.stop_reason == "refusal" or not response.content:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI declined this image — try a clearer screenshot",
        )

    text_blocks = [block.text for block in response.content if block.type == "text"]
    try:
        data = json.loads("".join(text_blocks))
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned an unreadable response — try again",
        ) from exc

    # De-duplicate case-insensitively, trim, and cap length + count so a hostile
    # or noisy image can't produce oversized names or an unbounded list.
    names: list[str] = []
    seen: set[str] = set()
    for raw in data.get("names", []):
        if not isinstance(raw, str):
            continue
        cleaned = raw.strip()[:80]
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(cleaned)
        if len(names) >= _MAX_NAMES:
            break
    return names
