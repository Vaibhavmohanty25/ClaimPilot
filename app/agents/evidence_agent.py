import json
from pathlib import Path

from app.services.llm import generate_text


BASE_DIR = Path(__file__).resolve().parent.parent

PROMPT_PATH = (
    BASE_DIR
    / "prompts"
    / "evidence_analysis.txt"
)


def load_prompt() -> str:
    return PROMPT_PATH.read_text(
        encoding="utf-8"
    )


def analyze_evidence(
    claim_reconstruction: dict,
    coverage_analysis: dict,
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
            "evidence_status": "WEAK",
            "evidence_confidence": 0.0,
            "contradictions": [],
            "unsupported_claim_items": [],
            "supported_claim_items": [],
            "missing_evidence": [],
            "risk_flags": [
                "Evidence Agent returned invalid JSON."
            ],
            "requires_human_review": True,
            "raw_response": response,
        }