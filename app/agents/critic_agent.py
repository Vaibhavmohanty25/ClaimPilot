import json
from pathlib import Path

from app.services.llm import generate_text
from app.services.evidence_semantics import (
    item_regions,
    is_visually_verifiable,
)


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

        filename = metadata.get(
            "filename"
        )

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


def _repair_estimate_has_labour(
    claim_reconstruction: dict,
) -> bool:
    for item in claim_reconstruction.get(
        "repair_estimate_items",
        [],
    ):
        if isinstance(item, dict):
            text = str(
                item.get(
                    "item",
                    "",
                )
            ).lower()
        else:
            text = str(
                item
            ).lower()

        if (
            "labour" in text
            or "labor" in text
        ):
            return True

    return False


def _flatten_text(
    value: object,
) -> str:
    if isinstance(value, dict):
        return " ".join(
            _flatten_text(item)
            for item in value.values()
        )

    if isinstance(value, list):
        return " ".join(
            _flatten_text(item)
            for item in value
        )

    return str(
        value
    )


def _contains_false_missing_estimate_claim(
    evidence_analysis: dict,
    missing_information: dict,
    has_repair_estimate: bool,
) -> bool:
    if not has_repair_estimate:
        return False

    text = (
        _flatten_text(
            evidence_analysis
        )
        + " "
        + _flatten_text(
            missing_information
        )
    ).lower()

    estimate_reference = (
        "repair estimate" in text
        or "repair_estimate" in text
    )

    missing_language = any(
        phrase in text
        for phrase in (
            "missing",
            "not provided",
            "not supplied",
            "absent",
            "unavailable",
        )
    )

    return (
        estimate_reference
        and missing_language
    )


def _contains_false_missing_police_report_claim(
    evidence_analysis: dict,
    missing_information: dict,
    has_police_report: bool,
) -> bool:
    if not has_police_report:
        return False

    text = (
        _flatten_text(
            evidence_analysis
        )
        + " "
        + _flatten_text(
            missing_information
        )
    ).lower()

    report_reference = (
        "police report" in text
        or "police_report" in text
    )

    missing_language = any(
        phrase in text
        for phrase in (
            "missing",
            "not provided",
            "not supplied",
            "absent",
            "unavailable",
        )
    )

    return (
        report_reference
        and missing_language
    )


def _contains_false_visual_labour_claim(
    evidence_analysis: dict,
    cross_modal_analysis: dict,
    labour_documented: bool,
) -> bool:
    if not labour_documented:
        return False

    text = (
        _flatten_text(
            evidence_analysis
        )
        + " "
        + _flatten_text(
            cross_modal_analysis
        )
    ).lower()

    labour_reference = (
        "labour" in text
        or "labor" in text
    )

    visual_language = any(
        phrase in text
        for phrase in (
            "no photo",
            "no photograph",
            "no visual",
            "visual evidence",
            "visually unsupported",
            "not visible",
        )
    )

    unsupported_language = any(
        phrase in text
        for phrase in (
            "unsupported",
            "unverified",
            "unverifiable",
            "not supported",
        )
    )

    return (
        labour_reference
        and visual_language
        and unsupported_language
    )


def _claim_is_blocked(
    missing_information: dict,
) -> bool:
    readiness = str(
        missing_information.get(
            "claim_readiness",
            "",
        )
    ).upper()

    blocking_issues = (
        missing_information.get(
            "blocking_issues",
            [],
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


def _append_issue(
    result: dict,
    issue: str,
) -> None:
    issues = list(
        result.get(
            "issues_found",
            [],
        )
        or []
    )

    if issue not in issues:
        issues.append(
            issue
        )

    result[
        "issues_found"
    ] = issues


def _require_revision(
    result: dict,
) -> None:
    result[
        "verification_status"
    ] = "REVISION_REQUIRED"

    result[
        "final_recommendation_valid"
    ] = False


def critique_adjudication(
    claim_reconstruction: dict,
    coverage_analysis: dict,
    evidence_analysis: dict,
    missing_information: dict,
    adjudication: dict,
    cross_modal_analysis: dict | None = None,
    files_processed: list | None = None,
    document_metadata: list | None = None,
) -> dict:

    cross_modal_analysis = (
        cross_modal_analysis or {}
    )

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
        .replace(
            "{cross_modal_analysis}",
            json.dumps(
                cross_modal_analysis,
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
            "\n\nCritic grounding rules:\n"
            "- Verify downstream claims against the actual uploaded files.\n"
            "- Do not accept a claim that the repair estimate is missing "
            "when it was uploaded or successfully reconstructed.\n"
            "- Labour and service costs do not require photographic evidence.\n"
            "- A region that was not visible is not the same as a region "
            "shown intact.\n"
            "- A NOT_READY claim with material blocking issues must not "
            "receive a final payable amount.\n"
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
                "Critic Agent returned non-object JSON."
            )

        # --------------------------------------------------
        # Existing visual consistency checks
        # --------------------------------------------------

        unsupported_regions = set()

        for item in cross_modal_analysis.get(
            "visually_unsupported_items",
            [],
        ):
            unsupported_regions.update(
                item_regions(
                    item
                )
            )

        approved_regions = set()

        for item in adjudication.get(
            "supported_damage_items",
            [],
        ):
            approved_regions.update(
                item_regions(
                    item
                )
            )

        for item in adjudication.get(
            "supported_repair_items",
            [],
        ):
            approved_regions.update(
                item_regions(
                    item
                )
            )

        conflicts = (
            unsupported_regions
            & approved_regions
        )

        if (
            cross_modal_analysis.get(
                "requires_human_review"
            )
            and not adjudication.get(
                "human_review_required"
            )
        ):
            _require_revision(
                result
            )

            result[
                "human_review_handled_correctly"
            ] = False

            _append_issue(
                result,
                "Uncertain visual evidence requires human review.",
            )

        if conflicts:
            _require_revision(
                result
            )

            result[
                "adjudication_consistent_with_evidence"
            ] = False

            _append_issue(
                result,
                (
                    "Adjudication approves visually unsupported damage: "
                    + ", ".join(
                        sorted(
                            conflicts
                        )
                    )
                ),
            )

            result[
                "recommended_correction"
            ] = (
                "Remove, adjust, or escalate visually unsupported repair items."
            )

        # --------------------------------------------------
        # Phase 2.1 source-of-truth grounding
        # --------------------------------------------------

        uploaded_files = (
            _uploaded_filenames(
                files_processed,
                document_metadata,
            )
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

        labour_documented = (
            has_repair_estimate
            and _repair_estimate_has_labour(
                claim_reconstruction
            )
        )

        if _contains_false_missing_estimate_claim(
            evidence_analysis,
            missing_information,
            has_repair_estimate,
        ):
            _require_revision(
                result
            )

            result[
                "adjudication_consistent_with_evidence"
            ] = False

            _append_issue(
                result,
                (
                    "Repair estimate was uploaded or successfully parsed, "
                    "but downstream reasoning incorrectly treats it as missing."
                ),
            )

        if _contains_false_missing_police_report_claim(
            evidence_analysis,
            missing_information,
            has_police_report,
        ):
            _require_revision(
                result
            )

            result[
                "adjudication_consistent_with_evidence"
            ] = False

            _append_issue(
                result,
                (
                    "Police report was uploaded or used during reconstruction, "
                    "but downstream reasoning incorrectly treats it as missing."
                ),
            )

        if _contains_false_visual_labour_claim(
            evidence_analysis,
            cross_modal_analysis,
            labour_documented,
        ):
            _require_revision(
                result
            )

            result[
                "adjudication_consistent_with_evidence"
            ] = False

            _append_issue(
                result,
                (
                    "Document-supported labour charges were incorrectly treated "
                    "as requiring photographic evidence."
                ),
            )

        # --------------------------------------------------
        # Non-visual items must not be treated as visually
        # unsupported/unverifiable.
        # --------------------------------------------------

        for bucket in (
            "visually_unsupported_items",
            "unverifiable_items",
        ):
            for item in cross_modal_analysis.get(
                bucket,
                [],
            ):
                text = (
                    item.get(
                        "item",
                        "",
                    )
                    if isinstance(
                        item,
                        dict,
                    )
                    else str(
                        item
                    )
                )

                if not is_visually_verifiable(
                    text
                ):
                    _require_revision(
                        result
                    )

                    result[
                        "adjudication_consistent_with_evidence"
                    ] = False

                    _append_issue(
                        result,
                        (
                            f"Non-visual item '{text}' was incorrectly "
                            f"placed in {bucket}."
                        ),
                    )

        # --------------------------------------------------
        # NOT_READY claim must not have a final settlement
        # amount.
        # --------------------------------------------------

        if (
            _claim_is_blocked(
                missing_information
            )
            and adjudication.get(
                "recommended_payable_amount"
            )
            is not None
        ):
            _require_revision(
                result
            )

            _append_issue(
                result,
                (
                    "A claim with material blocking issues has a final "
                    "recommended payable amount."
                ),
            )

            result[
                "recommended_correction"
            ] = (
                "Remove the final payable amount until blocking issues are resolved."
            )

        return result

    except (
        json.JSONDecodeError,
        ValueError,
    ):
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