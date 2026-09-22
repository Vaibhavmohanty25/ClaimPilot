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


def _uploaded_filenames(
    files_processed: list | None,
    document_metadata: list | None,
) -> set[str]:
    """
    Build a normalized set of filenames that are known
    to have been uploaded/processed.
    """

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


def _contains_repair_estimate(
    claim_reconstruction: dict,
    uploaded_files: set[str],
) -> bool:
    """
    Determine whether a usable repair estimate is actually
    present in the grounded claim state.
    """

    uploaded_estimate = any(
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
        uploaded_estimate
        or extracted_items
        or extracted_total
    )


def _contains_police_report(
    claim_reconstruction: dict,
    uploaded_files: set[str],
) -> bool:
    """
    Determine whether a police report was actually supplied
    or contributed to reconstruction.
    """

    uploaded_report = any(
        "police_report" in filename
        or "police report" in filename
        for filename in uploaded_files
    )

    if uploaded_report:
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


def _item_text(
    item: object,
) -> str:
    """
    Extract a useful item name from either a string
    or structured evidence item.
    """

    if isinstance(item, str):
        return item

    if isinstance(item, dict):
        return str(
            item.get("item")
            or item.get("name")
            or item.get("description")
            or ""
        )

    return str(item)


def _is_labour_item(
    item: object,
) -> bool:
    text = _item_text(item).lower()

    return (
        "labour" in text
        or "labor" in text
    )


def _repair_estimate_has_labour(
    claim_reconstruction: dict,
) -> bool:
    """
    Check whether labour is explicitly documented in the
    parsed repair estimate.
    """

    for item in claim_reconstruction.get(
        "repair_estimate_items",
        [],
    ):
        if _is_labour_item(item):
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
    """
    Preserve order while removing obvious duplicates.
    """

    result = []
    seen = set()

    for item in items:
        key = json.dumps(
            item,
            sort_keys=True,
        ) if isinstance(
            item,
            (dict, list),
        ) else str(item).lower().strip()

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
    """
    Deterministically correct evidence-agent claims that
    contradict the actual processed claim state.

    This protects downstream agents from LLM drift.
    """

    uploaded_files = _uploaded_filenames(
        files_processed,
        document_metadata,
    )

    has_repair_estimate = (
        _contains_repair_estimate(
            claim_reconstruction,
            uploaded_files,
        )
    )

    has_police_report = (
        _contains_police_report(
            claim_reconstruction,
            uploaded_files,
        )
    )

    has_documented_labour = (
        has_repair_estimate
        and _repair_estimate_has_labour(
            claim_reconstruction
        )
    )

    # ---------------------------------------------
    # Remove false "missing evidence" conclusions.
    # ---------------------------------------------

    missing_evidence = list(
        analysis.get(
            "missing_evidence",
            [],
        )
        or []
    )

    filtered_missing = []

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

        filtered_missing.append(
            item
        )

    analysis[
        "missing_evidence"
    ] = _deduplicate(
        filtered_missing
    )

    # ---------------------------------------------
    # Repair-estimate labour is document-supported.
    # ---------------------------------------------

    unsupported = list(
        analysis.get(
            "unsupported_claim_items",
            [],
        )
        or []
    )

    supported = list(
        analysis.get(
            "supported_claim_items",
            [],
        )
        or []
    )

    filtered_unsupported = []

    for item in unsupported:
        if (
            has_documented_labour
            and _is_labour_item(item)
        ):
            continue

        filtered_unsupported.append(
            item
        )

    if has_documented_labour:
        labour_already_supported = any(
            _is_labour_item(item)
            for item in supported
        )

        if not labour_already_supported:
            supported.append(
                "Labour charges"
            )

    analysis[
        "unsupported_claim_items"
    ] = _deduplicate(
        filtered_unsupported
    )

    analysis[
        "supported_claim_items"
    ] = _deduplicate(
        supported
    )

    return analysis


def analyze_evidence(
    claim_reconstruction: dict,
    coverage_analysis: dict,
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
    )

    # Give the LLM the same source-of-truth metadata
    # that deterministic post-processing will enforce.
    prompt += (
        "\n\nSOURCE-OF-TRUTH DOCUMENT METADATA:\n"
        + json.dumps(
            grounding_context,
            indent=2,
        )
        + (
            "\n\nImportant grounding rules:\n"
            "- Do not call an uploaded and successfully parsed document missing.\n"
            "- A repair estimate is valid documentary evidence for its "
            "listed repair items and labour charges.\n"
            "- Labour does not require photographic confirmation.\n"
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

    if not isinstance(
        analysis,
        dict,
    ):
        return {
            "evidence_status": "WEAK",
            "evidence_confidence": 0.0,
            "contradictions": [],
            "unsupported_claim_items": [],
            "supported_claim_items": [],
            "missing_evidence": [],
            "risk_flags": [
                "Evidence Agent returned an invalid response structure."
            ],
            "requires_human_review": True,
            "raw_response": response,
        }

    return _apply_grounding_guard(
        analysis,
        claim_reconstruction,
        files_processed,
        document_metadata,
    )