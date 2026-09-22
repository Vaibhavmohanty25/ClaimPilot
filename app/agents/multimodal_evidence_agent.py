import json
from pathlib import Path

from app.services.llm import generate_text
from app.services.evidence_semantics import apply_visual_visibility_guard


BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = BASE_DIR / "prompts" / "multimodal_evidence.txt"


def no_visual_evidence_result() -> dict:
    return {
        "cross_modal_status": "INSUFFICIENT_VISUAL_EVIDENCE",
        "cross_modal_confidence": 0.0,
        "supported_items": [],
        "partially_supported_items": [],
        "visually_unsupported_items": [],
        "unverifiable_items": [],
        "cross_modal_contradictions": [],
        "risk_flags": [],
        "requires_human_review": False,
    }


def analyze_cross_modal_evidence(
    claim_reconstruction: dict,
    evidence_analysis: dict,
    visual_analysis: dict,
) -> dict:
    if not visual_analysis.get("images_analyzed"):
        result = no_visual_evidence_result()
        result["requires_human_review"] = bool(visual_analysis.get("requires_human_review"))
        return result

    if visual_analysis.get("visual_confidence") == 0 and visual_analysis.get("requires_human_review"):
        return {**no_visual_evidence_result(), "requires_human_review": True,
                "unverifiable_items": claim_reconstruction.get("reported_damage", []),
                "risk_flags": ["Visual evidence could not be verified."]}

    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = prompt.replace("{claim_reconstruction}", json.dumps(claim_reconstruction, indent=2))
    prompt = prompt.replace("{evidence_analysis}", json.dumps(evidence_analysis, indent=2))
    prompt = prompt.replace("{visual_analysis}", json.dumps(visual_analysis, indent=2))
    try:
        response = generate_text(prompt)
        result = json.loads(response.replace("```json", "").replace("```", "").strip())
        if not isinstance(result, dict) or not no_visual_evidence_result().keys() <= result.keys():
            raise ValueError("Invalid cross-modal structure")
        if type(result["requires_human_review"]) is not bool:
            raise ValueError("Invalid review flag")
        for key in ("supported_items", "partially_supported_items", "visually_unsupported_items", "unverifiable_items", "cross_modal_contradictions", "risk_flags"):
            if key in result and not isinstance(result[key], list):
                raise ValueError("Invalid cross-modal list")
        return apply_visual_visibility_guard(result, visual_analysis)
    except (ValueError, TypeError, AttributeError, RuntimeError):
        return {
            **no_visual_evidence_result(),
            "cross_modal_status": "WEAK_ALIGNMENT",
            "risk_flags": ["Cross-Modal Evidence Agent returned invalid JSON."],
            "requires_human_review": True,
        }
