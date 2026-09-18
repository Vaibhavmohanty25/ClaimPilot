import json
from pathlib import Path

from app.services.llm import generate_text


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


def adjudicate_claim(
    claim_reconstruction: dict,
    coverage_analysis: dict,
    evidence_analysis: dict,
    missing_information: dict,
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
    )

    response = generate_text(prompt)

    cleaned = (
        response
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:
        return json.loads(cleaned)

    except json.JSONDecodeError:
        return {
            "recommendation": "ESCALATE_FOR_HUMAN_REVIEW",
            "adjudication_confidence": 0.0,
            "coverage_position": "",
            "supported_damage_items": [],
            "disputed_damage_items": [],
            "recommended_payable_amount": None,
            "reasoning": [
                "Adjudication Agent returned invalid JSON."
            ],
            "human_review_required": True,
            "next_action": "Human adjuster review required.",
            "raw_response": response,
        }