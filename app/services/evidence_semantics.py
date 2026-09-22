REGION_PHRASES = {
    "door": "door",
    "front bumper": "front_bumper",
    "rear bumper": "rear_bumper",
    "left headlamp": "left_headlamp",
    "right headlamp": "right_headlamp",
    "bonnet": "bonnet",
    "left front fender": "left_front_fender",
    "right front fender": "right_front_fender",
    "windscreen": "windscreen",
}


NON_VISUAL_TERMS = {
    "labour",
    "labor",
    "tax",
    "gst",
    "workshop fee",
    "workshop fees",
    "diagnostic",
    "diagnostic fee",
    "diagnostic fees",
    "towing",
    "towing fee",
    "towing fees",
    "administrative fee",
    "administrative fees",
    "service charge",
    "service charges",
}


def _item_text(value: object) -> str:
    """
    Convert an evidence item into a comparable text representation.
    """

    if isinstance(value, dict):
        value = (
            value.get("item")
            or value.get("region")
            or value.get("description")
            or ""
        )

    if not isinstance(value, str):
        return ""

    return value.strip()


def item_regions(value: object) -> set[str]:
    """
    Return normalized vehicle regions referenced by an evidence item.
    """

    text = _item_text(value)

    if not text:
        return set()

    normalized = (
        text
        .lower()
        .replace("_", " ")
    )

    return {
        region
        for phrase, region in REGION_PHRASES.items()
        if phrase in normalized
    }


def is_visually_verifiable(item: str) -> bool:
    """
    Return False for service, financial, or administrative
    costs that cannot meaningfully be verified from vehicle
    damage photographs.

    Physical vehicle components remain visually verifiable.
    """

    if not item:
        return False

    normalized = item.lower().strip()

    return not any(
        term in normalized
        for term in NON_VISUAL_TERMS
    )


def _semantic_key(value: object) -> str:
    """
    Produce a stable semantic identity for deduplication.

    Vehicle-region identity takes priority so that values such as:

        "left headlamp"
        "Left headlamp assembly"

    are treated as the same visual evidence item.
    """

    regions = item_regions(value)

    if regions:
        return "|".join(sorted(regions))

    text = _item_text(value).lower()

    removable_terms = (
        "replacement",
        "assembly",
        "repair",
        "repairs",
        "replace",
        "replaced",
    )

    for term in removable_terms:
        text = text.replace(
            term,
            " ",
        )

    return " ".join(
        text.split()
    )


def _deduplicate(items: list) -> list:
    """
    Deduplicate evidence items while preserving order.
    """

    result = []
    seen = set()

    for item in items:
        key = _semantic_key(item)

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)
        result.append(item)

    return result


def apply_visual_visibility_guard(
    analysis: dict,
    visual_analysis: dict,
) -> dict:
    """
    Enforce ClaimPilot's visual evidence semantics.

    Rules:
    - not visible != not damaged
    - non-visual costs must not require photographic evidence
    - only reliably visible/intact regions may be visually unsupported
    - visually unsupported/unverifiable lists are semantically deduplicated
    """

    unsupported = list(
        analysis.get(
            "visually_unsupported_items",
            [],
        )
    )

    unverifiable = list(
        analysis.get(
            "unverifiable_items",
            [],
        )
    )

    # --------------------------------------------------
    # Remove non-visual service/financial items from
    # both visual evidence buckets.
    # --------------------------------------------------

    unsupported = [
        item
        for item in unsupported
        if is_visually_verifiable(
            _item_text(item)
        )
    ]

    unverifiable = [
        item
        for item in unverifiable
        if is_visually_verifiable(
            _item_text(item)
        )
    ]

    observations = (
        visual_analysis.get(
            "image_observations"
        )
        or [visual_analysis]
    )

    visibly_intact = set()
    reliably_damaged = set()

    # --------------------------------------------------
    # Build reliable visual state
    # --------------------------------------------------

    for observation in observations:
        confidence = observation.get(
            "visual_confidence",
            0,
        )

        if not (
            type(confidence) in (int, float)
            and 0.8 <= confidence <= 1
            and not observation.get(
                "image_quality_issues"
            )
            and observation.get(
                "vehicle_visible",
                True,
            )
        ):
            continue

        not_visible = set(
            observation.get(
                "regions_not_visible",
                [],
            )
        )

        visibly_intact.update(
            set(
                observation.get(
                    "regions_visible_intact",
                    [],
                )
            )
            - not_visible
        )

        for item in observation.get(
            "visible_damage",
            [],
        ):
            item_confidence = (
                item.get(
                    "confidence",
                    0,
                )
                if isinstance(
                    item,
                    dict,
                )
                else 0
            )

            if (
                type(item_confidence)
                in (int, float)
                and 0.8 <= item_confidence <= 1
            ):
                reliably_damaged.update(
                    item_regions(item)
                    - not_visible
                )

    # A region cannot simultaneously be considered
    # reliably damaged and visibly intact.
    visibly_intact -= reliably_damaged

    # --------------------------------------------------
    # Validate visually unsupported items
    # --------------------------------------------------

    retained_unsupported = []

    for item in unsupported:
        regions = item_regions(item)

        can_be_visually_unsupported = (
            bool(regions)
            and regions <= visibly_intact
        )

        if can_be_visually_unsupported:
            retained_unsupported.append(
                item
            )

        else:
            # Region is absent/not visible rather than
            # confidently shown intact.
            unverifiable.append(
                item
            )

    # --------------------------------------------------
    # Validate supported / partially-supported items
    # --------------------------------------------------

    for key in (
        "supported_items",
        "partially_supported_items",
    ):
        if key not in analysis:
            continue

        retained_supported = []

        for item in analysis[key]:
            text = _item_text(item)

            # Labour/taxes/etc. may remain supported
            # through documentary evidence.
            if not is_visually_verifiable(
                text
            ):
                retained_supported.append(
                    item
                )
                continue

            regions = item_regions(item)

            if (
                regions
                and regions <= reliably_damaged
            ):
                retained_supported.append(
                    item
                )

            else:
                unverifiable.append(
                    item
                )

                analysis[
                    "cross_modal_status"
                ] = "PARTIAL_ALIGNMENT"

        analysis[key] = _deduplicate(
            retained_supported
        )

    # --------------------------------------------------
    # Deduplicate visual result buckets
    # --------------------------------------------------

    retained_unsupported = _deduplicate(
        retained_unsupported
    )

    unverifiable = _deduplicate(
        unverifiable
    )

    # Ensure the same semantic item does not appear in
    # both unsupported and unverifiable buckets.
    unsupported_keys = {
        _semantic_key(item)
        for item in retained_unsupported
    }

    unverifiable = [
        item
        for item in unverifiable
        if _semantic_key(item)
        not in unsupported_keys
    ]

    analysis[
        "visually_unsupported_items"
    ] = retained_unsupported

    analysis[
        "unverifiable_items"
    ] = unverifiable

    # --------------------------------------------------
    # Confidence sanitation
    # --------------------------------------------------

    confidence = analysis.get(
        "cross_modal_confidence",
        0,
    )

    visual_confidence = (
        visual_analysis.get(
            "visual_confidence",
            0,
        )
    )

    if (
        type(confidence)
        not in (int, float)
        or not 0 <= confidence <= 1
    ):
        confidence = 0

    if (
        type(visual_confidence)
        not in (int, float)
        or not 0 <= visual_confidence <= 1
    ):
        visual_confidence = 0

    analysis[
        "cross_modal_confidence"
    ] = min(
        confidence,
        visual_confidence,
    )

    # --------------------------------------------------
    # Validate contradictions
    # --------------------------------------------------

    contradictions = analysis.get(
        "cross_modal_contradictions",
        [],
    )

    retained_contradictions = []

    for item in contradictions:
        text = _item_text(item)

        # Non-visual charges cannot create a visual
        # contradiction.
        if not is_visually_verifiable(
            text
        ):
            continue

        regions = item_regions(item)

        if (
            regions
            and regions <= visibly_intact
        ):
            retained_contradictions.append(
                item
            )

    retained_contradictions = (
        _deduplicate(
            retained_contradictions
        )
    )

    analysis[
        "cross_modal_contradictions"
    ] = retained_contradictions

    if (
        len(retained_contradictions)
        != len(contradictions)
    ):
        analysis[
            "requires_human_review"
        ] = True

        analysis[
            "cross_modal_status"
        ] = "PARTIAL_ALIGNMENT"

    # --------------------------------------------------
    # Final safety rules
    # --------------------------------------------------

    if (
        unverifiable
        or visual_analysis.get(
            "requires_human_review"
        )
    ):
        analysis[
            "requires_human_review"
        ] = True

    if (
        unsupported
        and not retained_unsupported
        and not retained_contradictions
    ):
        analysis[
            "cross_modal_status"
        ] = "PARTIAL_ALIGNMENT"

    if (
        analysis.get(
            "cross_modal_status"
        )
        == "CONTRADICTORY"
        and not retained_unsupported
        and not retained_contradictions
    ):
        analysis[
            "cross_modal_status"
        ] = "PARTIAL_ALIGNMENT"

        analysis[
            "requires_human_review"
        ] = True

    return analysis