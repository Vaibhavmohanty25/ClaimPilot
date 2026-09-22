import os

from dotenv import load_dotenv
from groq import Groq

from app.services.provider_retry import (
    request_with_retry,
)


load_dotenv()


GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY"
)

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b",
).strip()


if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is missing from your .env file."
    )


if not GROQ_MODEL:
    raise RuntimeError(
        "GROQ_MODEL is required for text generation."
    )


client = Groq(
    api_key=GROQ_API_KEY,
    max_retries=0,
)


def _configured_text_attempts() -> int:
    """
    Default remains 3 so offline hardening guarantees
    stay unchanged.

    The live API may opt into a larger retry budget with:

        CLAIMPILOT_TEXT_MAX_ATTEMPTS=4
    """

    raw = os.getenv(
        "CLAIMPILOT_TEXT_MAX_ATTEMPTS",
        "3",
    )

    try:
        value = int(raw)
    except ValueError:
        return 3

    if not 1 <= value <= 5:
        return 3

    return value


def generate_text(
    prompt: str,
    max_retries: int | None = None,
) -> str:
    """
    Generate text using Groq through ClaimPilot's shared
    hardened provider retry service.
    """

    if not isinstance(
        prompt,
        str,
    ):
        raise TypeError(
            "Prompt must be a string."
        )

    if not prompt.strip():
        raise ValueError(
            "Prompt must not be empty."
        )

    max_attempts = (
        max_retries
        if max_retries is not None
        else _configured_text_attempts()
    )

    return request_with_retry(
        lambda: client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.2,
        ),
        model=GROQ_MODEL,
        stage="text_llm",
        max_attempts=max_attempts,
        image_count=0,
    )