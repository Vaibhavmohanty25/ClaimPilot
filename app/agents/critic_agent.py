import json
from pathlib import Path

from app.services.llm import generate_text


BASE_DIR = Path(__file__).resolve().parent.parent

PROMPT_PATH = (
    BASE_DIR
    / "prompts"
    / "critic.txt"
)


def load_prompt() -> str:
    return PROMPT_PATH.read_text(
        encoding="utf-8"
    )


def critique_adjudication(
    claim_reconstruction: dict,
    coverage_analysis: dict,
    evidence_analysis: dict,
    missing_information: dict,
    adjudication: dict,
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
            "{adjudication}",
            json.dumps(
                adjudication,
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
            "verification_status": "REVISION_REQUIRED",
            "critic_confidence": 0.0,
            "issues_found": [
                "Critic Agent returned invalid JSON."
            ],
            "unsupported_conclusions": [],
            "adjudication_consistent_with_evidence": False,
            "adjudication_consistent_with_policy": False,
            "human_review_handled_correctly": False,
            "recommended_correction": (
                "Send the claim for human review because "
                "the critic result could not be parsed."
            ),
            "final_recommendation_valid": False,
            "raw_response": response,
        }