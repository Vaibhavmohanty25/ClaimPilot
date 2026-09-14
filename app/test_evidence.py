from app.agents.evidence_agent import analyze_evidence


claim_reconstruction = {
    "claim_type": "Motor",
    "incident_summary": (
        "The claimant's Hyundai Creta was struck on the front-left side."
    ),
    "incident_date": "3 September 2026",
    "incident_location": "Jalandhar, Punjab",
    "reported_damage": [
        "Front bumper damage",
        "Left headlamp damage",
        "Bonnet repair",
        "Rear bumper replacement",
    ],
    "claimed_amount": 82000,
    "uncertain_facts": [
        "Exact incident time",
    ],
    "initial_contradictions": [
        {
            "field": "Incident Time",
            "claim_form": "Approximately 9:15 PM",
            "police_report": "Approximately 6:50 PM",
        }
    ],
}


coverage_analysis = {
    "coverage_status": "LIKELY_COVERED",
    "coverage_confidence": 0.78,
    "reasoning": [
        "Collision damage appears covered under Own Damage Coverage."
    ],
    "applicable_deductible": None,
    "exclusions_triggered": [],
    "requires_human_review": False,
}


result = analyze_evidence(
    claim_reconstruction,
    coverage_analysis,
)

print(result)