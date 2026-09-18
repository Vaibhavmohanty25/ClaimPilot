from app.agents.adjudication_agent import adjudicate_claim


claim_reconstruction = {
    "claim_type": "Motor",
    "incident_summary": (
        "The claimant's Hyundai Creta was struck on the front-left side "
        "at an intersection in Jalandhar, resulting in damage to the "
        "front bumper and left headlamp."
    ),
    "incident_date": "3 September 2026",
    "incident_location": "Jalandhar, Punjab",
    "people_involved": [
        "Rahul Sharma"
    ],
    "vehicles_involved": [
        {
            "make": "Hyundai",
            "model": "Creta",
            "registration": "PB10AB1234",
        }
    ],
    "reported_damage": [
        "front bumper",
        "left headlamp",
        "bonnet",
        "rear bumper",
    ],
    "claimed_amount": 82000,
    "uncertain_facts": [
        "Exact time of the accident",
        "Whether bonnet and rear bumper damage occurred in the collision",
    ],
    "initial_contradictions": [
        (
            "Incident time differs between claim form "
            "(9:15 PM) and police report (6:50 PM)."
        ),
        (
            "Repair estimate includes bonnet and rear bumper damage "
            "not mentioned in the initial claim or police report."
        ),
    ],
}


coverage_analysis = {
    "coverage_status": "LIKELY_COVERED",
    "coverage_confidence": 0.85,
    "reasoning": [
        (
            "The reported incident is an accidental collision "
            "covered under Own Damage Coverage."
        ),
        (
            "Unsupported repair items may be excluded from the "
            "payable claim amount."
        ),
    ],
    "applicable_deductible": None,
    "exclusions_triggered": [],
    "policy_evidence": [
        "SECTION 2 - OWN DAMAGE COVERAGE",
        "SECTION 3 - COLLISION DAMAGE",
        "SECTION 7 - CLAIM ASSESSMENT",
    ],
    "requires_human_review": False,
}


evidence_analysis = {
    "evidence_status": "PARTIALLY_SUPPORTED",
    "evidence_confidence": 0.65,
    "contradictions": [
        (
            "Accident time differs between the claim form "
            "and police report."
        ),
        (
            "Bonnet and rear bumper damage are only present "
            "in the repair estimate."
        ),
    ],
    "unsupported_claim_items": [
        "Bonnet repair",
        "Rear bumper replacement",
    ],
    "supported_claim_items": [
        "Front bumper replacement",
        "Left headlamp replacement",
    ],
    "missing_evidence": [
        "Supporting evidence for bonnet damage",
        "Supporting evidence for rear bumper damage",
        "Clarification of the accident time",
    ],
    "risk_flags": [
        "Conflicting accident times",
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
        (
            "Clarify whether the accident occurred at "
            "6:50 PM or 9:15 PM."
        ),
        (
            "Clarify whether bonnet and rear bumper damage "
            "resulted from this collision."
        ),
    ],
    "blocking_issues": [
        "Conflicting accident time",
        "Unsupported repair items",
    ],
    "non_blocking_issues": [],
    "recommended_next_actions": [
        "Request clarification regarding the accident time.",
        "Request supporting evidence for bonnet damage.",
        "Request supporting evidence for rear bumper damage.",
    ],
    "ready_for_adjudication": False,
}


result = adjudicate_claim(
    claim_reconstruction,
    coverage_analysis,
    evidence_analysis,
    missing_information,
)


print("\n=== ADJUDICATION RESULT ===\n")
print(result)