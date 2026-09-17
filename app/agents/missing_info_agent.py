import json
from pathlib import Path

from app.services.llm import generate_text


BASE_DIR = Path(__file__).resolve().parent.parent

PROMPT_PATH = (
    BASE_DIR
    / "prompts"
    / "missing_information.txt"
)


def load_prompt() -> str:
    return PROMPT_PATH.read_text(
        encoding="utf-8"
    )


def analyze_missing_information(
    claim_reconstruction: dict,
    coverage_analysis: dict,
    evidence_analysis: dict,
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
            "claim_readiness": "INSUFFICIENT_INFORMATION",
            "missing_documents": [],
            "missing_evidence": [],
            "clarifications_needed": [],
            "blocking_issues": [
                "Missing Information Agent returned invalid JSON."
            ],
            "non_blocking_issues": [],
            "recommended_next_actions": [],
            "ready_for_adjudication": False,
            "raw_response": response,
        }