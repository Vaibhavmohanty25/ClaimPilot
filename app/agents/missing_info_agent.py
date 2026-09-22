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


def _uploaded_filenames(
    files_processed: list | None,
    document_metadata: list | None,
) -> set[str]:
    filenames: set[str] = set()

    for filename in files_processed or []:
        if isinstance(filename, str):
            filenames.add(
                filename.lower().strip()
            )

    for metadata in document_metadata or []:
        if not isinstance(metadata, dict):
            continue

        filename = metadata.get("filename")

        if isinstance(filename, str):
            filenames.add(
                filename.lower().strip()
            )

    return filenames


def _has_repair_estimate(
    claim_reconstruction: dict,
    uploaded_files: set[str],
) -> bool:
    uploaded = any(
        "repair_estimate" in filename
        or "repair estimate" in filename
        for filename in uploaded_files
    )

    extracted_items = bool(
        claim_reconstruction.get(
            "repair_estimate_items"
        )
    )

    extracted_total = (
        claim_reconstruction.get(
            "repair_estimate_total"
        )
        is not None
    )

    return (
        uploaded
        or extracted_items
        or extracted_total
    )


def _has_police_report(
    claim_reconstruction: dict,
    uploaded_files: set[str],
) -> bool:
    uploaded = any(
        "police_report" in filename
        or "police report" in filename
        for filename in uploaded_files
    )

    if uploaded:
        return True

    for event in claim_reconstruction.get(
        "timeline",
        [],
    ):
        if not isinstance(event, dict):
            continue

        source = str(
            event.get(
                "source",
                "",
            )
        ).lower()

        if (
            "police_report" in source
            or "police report" in source
        ):
            return True

    return False


def _mentions_repair_estimate(
    value: object,
) -> bool:
    text = str(value).lower()

    return (
        "repair estimate" in text
        or "repair_estimate" in text
    )


def _mentions_police_report(
    value: object,
) -> bool:
    text = str(value).lower()

    return (
        "police report" in text
        or "police_report" in text
    )


def _deduplicate(
    items: list,
) -> list:
    result = []
    seen = set()

    for item in items:
        if isinstance(
            item,
            (dict, list),
        ):
            key = json.dumps(
                item,
                sort_keys=True,
            )
        else:
            key = str(
                item
            ).lower().strip()

        if key in seen:
            continue

        seen.add(key)
        result.append(item)

    return result


def _apply_grounding_guard(
    analysis: dict,
    claim_reconstruction: dict,
    files_processed: list | None,
    document_metadata: list | None,
) -> dict:
    uploaded_files = _uploaded_filenames(
        files_processed,
        document_metadata,
    )

    has_repair_estimate = (
        _has_repair_estimate(
            claim_reconstruction,
            uploaded_files,
        )
    )

    has_police_report = (
        _has_police_report(
            claim_reconstruction,
            uploaded_files,
        )
    )

    missing_documents = list(
        analysis.get(
            "missing_documents",
            [],
        )
        or []
    )

    filtered_documents = []

    for item in missing_documents:
        if (
            has_repair_estimate
            and _mentions_repair_estimate(
                item
            )
        ):
            continue

        if (
            has_police_report
            and _mentions_police_report(
                item
            )
        ):
            continue

        filtered_documents.append(
            item
        )

    analysis[
        "missing_documents"
    ] = _deduplicate(
        filtered_documents
    )

    missing_evidence = list(
        analysis.get(
            "missing_evidence",
            [],
        )
        or []
    )

    filtered_evidence = []

    for item in missing_evidence:
        if (
            has_repair_estimate
            and _mentions_repair_estimate(
                item
            )
        ):
            continue

        if (
            has_police_report
            and _mentions_police_report(
                item
            )
        ):
            continue

        filtered_evidence.append(
            item
        )

    analysis[
        "missing_evidence"
    ] = _deduplicate(
        filtered_evidence
    )

    blocking_issues = list(
        analysis.get(
            "blocking_issues",
            [],
        )
        or []
    )

    filtered_blocking = []

    for item in blocking_issues:
        text = str(
            item
        ).lower()

        if (
            has_repair_estimate
            and _mentions_repair_estimate(
                item
            )
            and (
                "missing" in text
                or "absent" in text
                or "not provided" in text
            )
        ):
            continue

        if (
            has_police_report
            and _mentions_police_report(
                item
            )
            and (
                "missing" in text
                or "absent" in text
                or "not provided" in text
            )
        ):
            continue

        filtered_blocking.append(
            item
        )

    analysis[
        "blocking_issues"
    ] = _deduplicate(
        filtered_blocking
    )

    recommended_actions = list(
        analysis.get(
            "recommended_next_actions",
            [],
        )
        or []
    )

    filtered_actions = []

    for item in recommended_actions:
        text = str(
            item
        ).lower()

        if (
            has_repair_estimate
            and _mentions_repair_estimate(
                item
            )
            and (
                "obtain" in text
                or "provide" in text
                or "submit" in text
            )
        ):
            continue

        if (
            has_police_report
            and _mentions_police_report(
                item
            )
            and (
                "obtain" in text
                or "provide" in text
                or "submit" in text
            )
        ):
            continue

        filtered_actions.append(
            item
        )

    analysis[
        "recommended_next_actions"
    ] = _deduplicate(
        filtered_actions
    )

    return analysis


def analyze_missing_information(
    claim_reconstruction: dict,
    coverage_analysis: dict,
    evidence_analysis: dict,
    cross_modal_analysis: dict | None = None,
    files_processed: list | None = None,
    document_metadata: list | None = None,
) -> dict:

    prompt_template = load_prompt()

    grounding_context = {
        "files_processed": (
            files_processed or []
        ),
        "document_metadata": (
            document_metadata or []
        ),
    }

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
            "{cross_modal_analysis}",
            json.dumps(
                cross_modal_analysis or {},
                indent=2,
            ),
        )
    )

    prompt += (
        "\n\nSOURCE-OF-TRUTH DOCUMENT METADATA:\n"
        + json.dumps(
            grounding_context,
            indent=2,
        )
        + (
            "\n\nImportant grounding rules:\n"
            "- Do not request a document that is already uploaded and parsed.\n"
            "- If repair estimate items or totals were extracted, the repair "
            "estimate is present unless there is a specific readability or "
            "completeness problem.\n"
            "- Do not treat a police report as missing if it was uploaded or "
            "used as a reconstruction source.\n"
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

    if not isinstance(
        analysis,
        dict,
    ):
        return {
            "claim_readiness": "INSUFFICIENT_INFORMATION",
            "missing_documents": [],
            "missing_evidence": [],
            "clarifications_needed": [],
            "blocking_issues": [
                "Missing Information Agent returned an invalid response structure."
            ],
            "non_blocking_issues": [],
            "recommended_next_actions": [],
            "ready_for_adjudication": False,
            "raw_response": response,
        }

    return _apply_grounding_guard(
        analysis,
        claim_reconstruction,
        files_processed,
        document_metadata,
    )