import json
from pathlib import Path

from app.services.llm import generate_text


PROMPT_PATH = Path(
    "app/prompts/reconstruction.txt"
)


def load_prompt() -> str:
    return PROMPT_PATH.read_text(
        encoding="utf-8"
    )


def reconstruct_claim(
    claim_documents: str
) -> dict:

    prompt_template = load_prompt()

    prompt = prompt_template.replace(
        "{claim_documents}",
        claim_documents,
    )

    response = generate_text(prompt)

    cleaned = (
        response
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:
        result = json.loads(cleaned)
        if not isinstance(result, dict):
            raise ValueError("Reconstruction must be a JSON object.")
        return result

    except (json.JSONDecodeError, ValueError):
        return {
            "error": "Claim Reconstruction Agent returned invalid JSON.",
            "raw_response": response,
        }