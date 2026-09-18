import json
from pathlib import Path

from app.services.llm import generate_text
from app.rag.retriever import retrieve_policy_context


BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = BASE_DIR / "prompts" / "policy_reasoning.txt"


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def build_coverage_query(claim_reconstruction: dict) -> str:
    summary = claim_reconstruction.get("incident_summary", "")
    damages = claim_reconstruction.get("reported_damage", [])
    contradictions = claim_reconstruction.get(
        "initial_contradictions",
        [],
    )

    return f"""
Motor insurance coverage analysis.

Incident:
{summary}

Reported damage:
{damages}

Known contradictions:
{contradictions}

Retrieve policy sections relevant to:

- accidental collision
- own damage coverage
- collision damage
- exclusions
- repair assessment
- claim documentation
- unsupported repair items
"""


def build_deductible_query(claim_reconstruction: dict) -> str:
    claimed_amount = claim_reconstruction.get("claimed_amount")

    return f"""
Motor insurance deductible and settlement analysis.

Claimed amount:
{claimed_amount}

Retrieve policy sections specifically related to:

- compulsory deductible
- deductible amount
- policy excess
- compulsory excess
- settlement deduction
- payable amount
- own damage claim deductible
"""


def merge_policy_contexts(*groups: list) -> list:
    merged = []
    seen = set()

    for group in groups:
        for item in group:
            text = item.get("text", "").strip()

            if not text:
                continue

            if text in seen:
                continue

            seen.add(text)
            merged.append(item)

    return merged


def analyze_policy(claim_reconstruction: dict) -> dict:
    # Coverage retrieval
    coverage_context = retrieve_policy_context(
        query=build_coverage_query(
            claim_reconstruction
        ),
        limit=5,
    )

    # Dedicated deductible retrieval
    deductible_context = retrieve_policy_context(
        query=build_deductible_query(
            claim_reconstruction
        ),
        limit=6,
    )

    policy_context = merge_policy_contexts(
        deductible_context,
        coverage_context,
    )

    # Debug so we can confirm Section 5 is actually passed downstream
    print("\n=== POLICY CONTEXT ===")
    for item in policy_context:
        print(
            item.get("text", "")[:120],
            "\n"
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

    response = generate_text(prompt)

    cleaned = (
        response
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:
        analysis = json.loads(cleaned)

    except json.JSONDecodeError:
        analysis = {
            "coverage_status": "REQUIRES_REVIEW",
            "coverage_confidence": 0.0,
            "reasoning": [],
            "applicable_deductible": None,
            "exclusions_triggered": [],
            "policy_evidence": [],
            "requires_human_review": True,
            "error": (
                "Policy Reasoning Agent "
                "returned invalid JSON."
            ),
            "raw_response": response,
        }

    return {
        "policy_context": policy_context,
        "coverage_analysis": analysis,
    }