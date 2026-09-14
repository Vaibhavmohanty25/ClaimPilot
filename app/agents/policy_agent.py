import json
from pathlib import Path

from app.services.llm import generate_text
from app.rag.retriever import (
    retrieve_policy_context,
)


BASE_DIR = Path(
    __file__
).resolve().parent.parent

PROMPT_PATH = (
    BASE_DIR
    / "prompts"
    / "policy_reasoning.txt"
)


def load_prompt() -> str:

    return PROMPT_PATH.read_text(
        encoding="utf-8"
    )


def build_policy_query(
    claim_reconstruction: dict
) -> str:

    summary = (
        claim_reconstruction.get(
            "incident_summary",
            ""
        )
    )

    damages = (
        claim_reconstruction.get(
            "reported_damage",
            []
        )
    )

    contradictions = (
        claim_reconstruction.get(
            "initial_contradictions",
            []
        )
    )

    return f"""
Insurance coverage for this claim:

Incident:
{summary}

Reported damage:
{damages}

Contradictions:
{contradictions}

Retrieve relevant policy clauses regarding:
collision coverage,
own damage,
deductibles,
claim evidence,
exclusions,
and unsupported repair items.
"""


def analyze_policy(
    claim_reconstruction: dict
) -> dict:

    query = build_policy_query(
        claim_reconstruction
    )

    policy_context = (
        retrieve_policy_context(
            query=query,
            limit=4,
        )
    )

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
            "{policy_context}",
            json.dumps(
                policy_context,
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

        analysis = json.loads(
            cleaned
        )

    except json.JSONDecodeError:

        analysis = {
            "coverage_status":
                "REQUIRES_REVIEW",

            "error":
                "Policy agent returned invalid JSON.",

            "raw_response":
                response,
        }

    return {
        "policy_context":
            policy_context,

        "coverage_analysis":
            analysis,
    }