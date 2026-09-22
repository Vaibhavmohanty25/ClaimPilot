"""Shared hardened retry handling for Groq text and vision providers."""

import os
import time
from time import perf_counter

from groq import (
    APIConnectionError,
    APIStatusError,
)

from app.services.observability import log_event


class ProviderError(RuntimeError):
    """
    Sanitized provider error.

    Raw provider responses must never escape through the API.
    """

    pass


def _configured_text_429_backoff() -> list[int]:
    """
    Optional runtime-only backoff schedule.

    Example:
        CLAIMPILOT_TEXT_429_BACKOFF=10,20,35

    When unset, ClaimPilot preserves the tested exponential
    backoff behavior: 1, 2, 4, 8 seconds.
    """

    raw = os.getenv(
        "CLAIMPILOT_TEXT_429_BACKOFF",
        "",
    ).strip()

    if not raw:
        return []

    try:
        values = [
            int(value.strip())
            for value in raw.split(",")
            if value.strip()
        ]
    except ValueError:
        return []

    return [
        value
        for value in values
        if 1 <= value <= 120
    ]


def _retry_delay(
    *,
    stage: str,
    status: int | None,
    attempt: int,
) -> int:
    """
    Return retry delay.

    Default:
        1, 2, 4, 8 seconds

    Optional live text-429 override:
        CLAIMPILOT_TEXT_429_BACKOFF=10,20,35
    """

    if (
        stage == "text_llm"
        and status == 429
    ):
        configured = (
            _configured_text_429_backoff()
        )

        if configured:
            return configured[
                min(
                    attempt,
                    len(configured) - 1,
                )
            ]

    return min(
        2 ** attempt,
        8,
    )


def request_with_retry(
    operation,
    *,
    model,
    stage,
    max_attempts=3,
    image_count=0,
):
    """
    Execute a Groq operation with bounded retries.

    Transient:
        connection errors
        408
        429
        500
        502
        503
        504

    Permanent provider failures are sanitized.
    """

    if (
        type(max_attempts) is not int
        or not 1 <= max_attempts <= 5
    ):
        raise ValueError(
            "Provider attempts must be an integer between 1 and 5."
        )

    start = perf_counter()

    for attempt in range(
        max_attempts
    ):
        try:
            response = operation()

            content = (
                response
                .choices[0]
                .message
                .content
            )

            if (
                not isinstance(
                    content,
                    str,
                )
                or not content.strip()
            ):
                raise ProviderError(
                    "Provider returned an empty response."
                )

            log_event(
                stage,
                True,
                model=model,
                retry_count=attempt,
                image_count=image_count,
                duration_ms=round(
                    (
                        perf_counter()
                        - start
                    )
                    * 1000,
                    2,
                ),
            )

            return content

        except (
            APIConnectionError,
            APIStatusError,
        ) as error:
            status = getattr(
                error,
                "status_code",
                None,
            )

            transient = (
                isinstance(
                    error,
                    APIConnectionError,
                )
                or status
                in (
                    408,
                    429,
                    500,
                    502,
                    503,
                    504,
                )
            )

            code = {
                400: "invalid_request",
                401: "authentication_failed",
                403: "permission_denied",
                404: "model_not_found",
                408: "transient_provider_failure",
                422: "unsupported_format",
                429: "rate_limit",
                500: "transient_provider_failure",
                502: "transient_provider_failure",
                503: "transient_provider_failure",
                504: "transient_provider_failure",
            }.get(
                status,
                "transient_provider_failure",
            )

            log_event(
                stage,
                False,
                model=model,
                retry_count=attempt,
                image_count=image_count,
                error_code=code,
                duration_ms=round(
                    (
                        perf_counter()
                        - start
                    )
                    * 1000,
                    2,
                ),
            )

            if (
                not transient
                or attempt
                == max_attempts - 1
            ):
                raise ProviderError(
                    f"Groq {stage} failed: "
                    f"{code}; "
                    f"attempts={attempt + 1}. "
                    "Check model, credentials, "
                    "rate limits, or provider availability."
                ) from None

            delay = _retry_delay(
                stage=stage,
                status=status,
                attempt=attempt,
            )

            if (
                stage == "text_llm"
                and status == 429
            ):
                print(
                    "Groq text-model rate limit reached. "
                    f"Retrying in {delay} seconds..."
                )

            time.sleep(
                delay
            )

        except (
            IndexError,
            AttributeError,
            ProviderError,
        ):
            log_event(
                stage,
                False,
                model=model,
                retry_count=attempt,
                image_count=image_count,
                error_code="invalid_response",
                duration_ms=round(
                    (
                        perf_counter()
                        - start
                    )
                    * 1000,
                    2,
                ),
            )

            raise ProviderError(
                "Groq returned an empty or malformed response."
            ) from None

    raise ProviderError(
        "Groq provider retry budget was exhausted."
    )