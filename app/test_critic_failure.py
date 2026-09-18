from app.agents.critic_agent import critique_adjudication


claim_reconstruction = {
    "claim_type": "Motor",
    "incident_summary": (
        "Hyundai Creta involved in a front-left collision."
    ),
    "claimed_amount": 82000,
    "initial_contradictions": [
        (
            "Claim form reports the incident at 9:15 PM, "
            "while the police report reports 6:50 PM."
        ),
        (
            "Bonnet and rear bumper appear only in the "
            "repair estimate and are not supported by "
            "the initial claim or police report."
        ),
    ],
}


coverage_analysis = {
    "coverage_status": "LIKELY_COVERED",
    "coverage_confidence": 0.85,
    "applicable_deductible": 5000,
    "exclusions_triggered": [],
    "requires_human_review": False,
}


evidence_analysis = {
    "evidence_status": "PARTIALLY_SUPPORTED",
    "evidence_confidence": 0.65,

    "contradictions": [
        "Conflicting accident times: 9:15 PM vs 6:50 PM."
    ],

    "supported_claim_items": [
        "Front bumper",
        "Left headlamp",
    ],

    "unsupported_claim_items": [
        "Bonnet",
        "Rear bumper",
    ],

    "missing_evidence": [
        "Evidence supporting bonnet damage",
        "Evidence supporting rear bumper damage",
        "Clarification of the accident time",
    ],

    "risk_flags": [
        "Conflicting accident time",
        "Unsupported repair items",
    ],

    "requires_human_review": True,
}


missing_information = {
    "claim_readiness": "NOT_READY",

    "missing_documents": [],

    "missing_evidence": [
        "Evidence supporting bonnet damage",
        "Evidence supporting rear bumper damage",
    ],

    "clarifications_needed": [
        "Clarify the conflicting accident time."
    ],

    "blocking_issues": [
        "Conflicting accident time",
        "Unsupported bonnet and rear bumper damage",
    ],

    "non_blocking_issues": [],

    "recommended_next_actions": [
        "Clarify the incident time.",
        "Provide evidence supporting bonnet and rear bumper damage.",
    ],

    "ready_for_adjudication": False,
}


# ---------------------------------------------------------
# DELIBERATELY WRONG ADJUDICATION
# ---------------------------------------------------------

adjudication = {
    "recommendation": "APPROVE",

    "adjudication_confidence": 0.99,

    "coverage_position": (
        "The entire claim is fully covered and all repair "
        "items should be paid."
    ),

    "supported_damage_items": [
        "Front bumper",
        "Left headlamp",
        "Bonnet",
        "Rear bumper",
    ],

    "disputed_damage_items": [],

    # Deliberately wrong:
    # approves the entire claimed amount despite unsupported items
    # and even ignores the deductible.
    "recommended_payable_amount": 82000,

    "reasoning": [
        "The policy covers collision damage.",
        "All repair items are approved.",
        "No additional information is required.",
    ],

    # Deliberately wrong:
    # evidence agent explicitly requires human review.
    "human_review_required": False,

    "next_action": "Pay the full claim immediately.",
}


result = critique_adjudication(
    claim_reconstruction,
    coverage_analysis,
    evidence_analysis,
    missing_information,
    adjudication,
)


print("\n=== ADVERSARIAL CRITIC TEST ===\n")

print(result)