import json
from pathlib import Path

from app.services.llm import generate_text
from app.services.settlement_calculator import calculate_payable_amount


BASE_DIR = Path(__file__).resolve().parent.parent

PROMPT_PATH = (
    BASE_DIR
    / "prompts"
    / "adjudication.txt"
)


def load_prompt() -> str:
    return PROMPT_PATH.read_text(
        encoding="utf-8"
    )


def _claim_is_blocked(
    missing_information: dict,
) -> bool:
    """
    Return True when the claim is explicitly not ready
    for final settlement.
    """

    readiness = str(
        missing_information.get(
            "claim_readiness",
            ""
        )
    ).upper()

    blocking_issues = (
        missing_information.get(
            "blocking_issues",
            []
        )
        or []
    )

    ready_for_adjudication = (
        missing_information.get(
            "ready_for_adjudication"
        )
    )

    if readiness in {
        "NOT_READY",
        "INSUFFICIENT_INFORMATION",
    }:
        return True

    if blocking_issues:
        return True

    if ready_for_adjudication is False:
        return True

    return False


def adjudicate_claim(
    claim_reconstruction: dict,
    coverage_analysis: dict,
    evidence_analysis: dict,
    missing_information: dict,
    cross_modal_analysis: dict | None = None,
) -> dict:

    prompt_template = load_prompt()

    prompt = (
        prompt_template
        .replace(
            "{claim_reconstruction}",
            json.dumps(
                claim_reconstruction,
                indent=2,
            ),
        )
        .replace(
            "{coverage_analysis}",
            json.dumps(
                coverage_analysis,
                indent=2,
            ),
        )
        .replace(
            "{evidence_analysis}",
            json.dumps(
                evidence_analysis,
                indent=2,
            ),
        )
        .replace(
            "{missing_information}",
            json.dumps(
                missing_information,
                indent=2,
            ),
        )
        .replace(
            "{cross_modal_analysis}",
            json.dumps(
                cross_modal_analysis or {},
                indent=2,
            ),
        )
    )

    response = generate_text(
        prompt
    )

    cleaned = (
        response
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:
        result = json.loads(
            cleaned
        )

        if not isinstance(
            result,
            dict,
        ):
            raise ValueError(
                "Adjudication Agent returned non-object JSON."
            )

        selected_items = result.get(
            "supported_repair_items"
        )

        amounts = None

        if isinstance(
            selected_items,
            list,
        ):
            amounts = [
                (
                    item.get("amount")
                    if isinstance(
                        item,
                        dict,
                    )
                    else None
                )
                for item in selected_items
            ]

        # --------------------------------------------------
        # Phase 2.1 readiness guard
        # --------------------------------------------------

        if _claim_is_blocked(
            missing_information
        ):
            result[
                "recommended_payable_amount"
            ] = None

            result[
                "human_review_required"
            ] = True

            if result.get(
                "recommendation"
            ) == "APPROVE":
                result[
                    "recommendation"
                ] = "REQUEST_MORE_INFORMATION"

        else:
            result[
                "recommended_payable_amount"
            ] = calculate_payable_amount(
                amounts,
                coverage_analysis.get(
                    "applicable_deductible"
                ),
            )

        # --------------------------------------------------
        # Cross-modal review guard
        # --------------------------------------------------

        if (
            cross_modal_analysis or {}
        ).get(
            "requires_human_review"
        ):
            result[
                "human_review_required"
            ] = True

            if (
                result.get(
                    "recommendation"
                )
                == "APPROVE"
            ):
                result[
                    "recommendation"
                ] = "ESCALATE_FOR_HUMAN_REVIEW"

                result[
                    "recommended_payable_amount"
                ] = None

        return result

    except (
        json.JSONDecodeError,
        ValueError,
    ):
        return {
            "recommendation": "ESCALATE_FOR_HUMAN_REVIEW",
            "adjudication_confidence": 0.0,
            "coverage_position": "",
            "supported_damage_items": [],
            "supported_repair_items": [],
            "disputed_damage_items": [],
            "recommended_payable_amount": None,
            "reasoning": [
                "Adjudication Agent returned invalid JSON."
            ],
            "human_review_required": True,
            "next_action": "Human adjuster review required.",
            "raw_response": response,
        }