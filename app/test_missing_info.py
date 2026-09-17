from app.agents.missing_info_agent import (
    analyze_missing_information,
)


claim_reconstruction = {
    "claim_type": "Motor",
    "incident_summary": (
        "The claimant's Hyundai Creta was struck on the front-left side "
        "at an intersection in Jalandhar, Punjab."
    ),
    "incident_date": "3 September 2026",
    "incident_location": "Jalandhar, Punjab",
    "people_involved": [
        {
            "name": "Rahul Sharma",
            "role": "Claimant / Reporting driver",
        }
    ],
    "vehicles_involved": [
        {
            "make_model": "Hyundai Creta",
            "registration": "PB10AB1234",
            "role": "Insured vehicle",
        }
    ],
    "reported_damage": [
        "Front bumper",
        "Left headlamp",
        "Bonnet repair",
        "Rear bumper replacement",
    ],
    "claimed_amount": 82000,
    "uncertain_facts": [
        "Exact time of the accident",
        "Identity and details of the other vehicle involved",
    ],
    "initial_contradictions": [
        "Incident time differs between claim_form.txt "
        "(approximately 9:15 PM) and police_report.txt "
        "(approximately 6:50 PM)",
        "Repair estimate includes bonnet repair and rear bumper "
        "replacement not mentioned in the claim description "
        "or police report",
    ],
}


coverage_analysis = {
    "coverage_status": "LIKELY_COVERED",
    "coverage_confidence": 0.85,
    "reasoning": [
        (
            "The reported incident is consistent with accidental "
            "collision coverage under Own Damage Coverage."
        ),
        (
            "Unsupported repair items may still be excluded "
            "from the payable amount."
        ),
    ],
    "applicable_deductible": None,
    "exclusions_triggered": [],
    "requires_human_review": False,
}


evidence_analysis = {
    "evidence_status": "PARTIALLY_SUPPORTED",
    "evidence_confidence": 0.55,
    "contradictions": [
        (
            "Accident time differs between police_report.txt "
            "(approximately 6:50 PM) and claim_form.txt "
            "(approximately 9:15 PM)."
        ),
        (
            "Repair estimate lists bonnet repair and rear bumper "
            "replacement, which are not mentioned in the police "
            "report or the initial incident description."
        ),
    ],
    "unsupported_claim_items": [
        "Bonnet repair",
        "Rear bumper replacement",
    ],
    "supported_claim_items": [
        "Front bumper damage",
        "Left headlamp damage",
    ],
    "missing_evidence": [
        "Evidence supporting bonnet damage",
        "Evidence supporting rear bumper damage",
    ],
    "risk_flags": [
        "Conflicting accident times",
        "Repair items not corroborated by primary evidence",
        "Absence of information about the other vehicle",
    ],
    "requires_human_review": True,
}


result = analyze_missing_information(
    claim_reconstruction,
    coverage_analysis,
    evidence_analysis,
)

print(result)