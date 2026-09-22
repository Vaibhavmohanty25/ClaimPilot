import json
import hashlib
import math
import re
from pathlib import Path

from app.services.vision_llm import generate_vision_json, MAX_VISION_IMAGES
from app.services.observability import log_event
from app.services.provider_retry import ProviderError
from app.services.evidence_semantics import item_regions


BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = BASE_DIR / "prompts" / "visual_evidence.txt"


def neutral_visual_analysis() -> dict:
    return {
        "images_analyzed": [],
        "vehicle_visible": False,
        "vehicle_regions_visible": [],
        "visible_damage": [],
        "possibly_damaged_regions": [],
        "regions_not_visible": [],
        "regions_visible_intact": [],
        "image_quality_issues": [],
        "visual_contradictions": [],
        "visual_risk_flags": [],
        "visual_confidence": 0.0,
        "requires_human_review": False,
    }


def valid_confidence(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1


def failure_result(filename, reason="Visual evidence could not be validated; human review required."):
    result = neutral_visual_analysis()
    result.update(images_analyzed=[filename], requires_human_review=True, visual_risk_flags=[reason])
    return result


def parse_visual_response(response, filename):
    """Reject untrustworthy structures wholesale; never invent missing findings."""
    if not isinstance(response, str):
        raise ValueError("Missing response")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", response.strip(), flags=re.I)
    value = json.loads(cleaned)
    template = neutral_visual_analysis()
    if not isinstance(value, dict) or not template.keys() <= value.keys():
        raise ValueError("Missing visual fields")
    result = {key: value[key] for key in template}
    for key in ("vehicle_visible", "requires_human_review"):
        if type(result[key]) is not bool:
            raise ValueError("Invalid boolean")
    if not valid_confidence(result["visual_confidence"]):
        raise ValueError("Invalid confidence")
    for key, default in template.items():
        if not isinstance(default, list):
            continue
        if not isinstance(result[key], list):
            raise ValueError("Invalid visual list")
        if key != "visible_damage":
            if any(not isinstance(item, str) or not item.strip() for item in result[key]):
                raise ValueError("Invalid visual list entry")
            result[key] = list(dict.fromkeys(result[key]))
    if result["images_analyzed"] != [filename]:
        raise ValueError("Missing or incorrect image reference")
    findings = []
    required = {"region", "damage_type", "severity", "confidence", "source_image", "description"}
    for item in result["visible_damage"]:
        if not isinstance(item, dict) or not required <= item.keys():
            raise ValueError("Malformed damage entry")
        if not valid_confidence(item["confidence"]) or item["source_image"] != filename:
            raise ValueError("Invalid damage confidence or reference")
        if any(not isinstance(item[key], str) or not item[key].strip() for key in required - {"confidence"}):
            raise ValueError("Invalid damage fields")
        finding = {key: item[key] for key in required}
        if finding not in findings:
            findings.append(finding)
    result["visible_damage"] = findings
    if result["visual_confidence"] < 0.8 or result["image_quality_issues"]:
        result["requires_human_review"] = True
        result["visual_contradictions"] = []
        result["regions_not_visible"] = list(dict.fromkeys(result["regions_not_visible"] + result["regions_visible_intact"]))
        result["regions_visible_intact"] = []
    else:
        intact = set(result["regions_visible_intact"]) - set(result["regions_not_visible"])
        result["visual_contradictions"] = [item for item in result["visual_contradictions"] if item_regions(item) and item_regions(item) <= intact]
    return result


def analyze_visual_evidence(image_files: list[dict]) -> dict:
    if not image_files:
        return neutral_visual_analysis()
    if len(image_files) > MAX_VISION_IMAGES:
        result = failure_result("image", "Vision limit exceeded: at most 3 images per claim.")
        result["images_analyzed"] = []
        return result

    # Independent image observations preserve provenance and prevent a blurred
    # image from reducing the confidence of a clear view of the same region.
    observations = []
    seen = {}
    duplicates = []
    names = set()
    for index, item in enumerate(image_files, 1):
        filename = Path(str(item.get("filename") or f"image-{index}").replace("\\", "/")).name
        if filename in names:
            filename = f"{index}-{filename}"
        names.add(filename)
        try:
            path = Path(item["path"])
            signature = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else str(path)
            if signature in seen:
                duplicates.append({"source_image": filename, "duplicate_of": seen[signature]})
                continue
            seen[signature] = filename
            prompt = PROMPT_PATH.read_text(encoding="utf-8").replace("{image_filenames}", json.dumps([filename]))
            response = generate_vision_json(prompt, [str(path)])
            observation = parse_visual_response(response, filename)
            if item.get("classification") == "unknown_image":
                observation["requires_human_review"] = True
                observation["visual_risk_flags"].append("Image routing is uncertain; verify image purpose.")
            log_event("vision_validation", True, image_count=1)
        except Exception as error:
            reason = str(error) if isinstance(error, ProviderError) else "Visual evidence could not be validated; human review required."
            observation = failure_result(filename, reason)
            log_event("vision_validation", False, image_count=1, error_code="unreliable_visual_result")
        observations.append(observation)

    result = neutral_visual_analysis()
    for observation in observations:
        for key, value in observation.items():
            if isinstance(value, list):
                for entry in value:
                    if entry not in result[key]:
                        result[key].append(entry)
        result["vehicle_visible"] |= observation["vehicle_visible"]
        result["requires_human_review"] |= observation["requires_human_review"]
        result["visual_confidence"] = max(result["visual_confidence"], observation["visual_confidence"])
    visible = set(result["vehicle_regions_visible"])
    damaged = {item["region"] for item in result["visible_damage"]}
    visible.update(damaged)
    visible.update(result["regions_visible_intact"])
    result["vehicle_regions_visible"] = sorted(visible)
    result["regions_not_visible"] = sorted(set(result["regions_not_visible"]) - visible)
    reliable_damage = {item["region"] for observation in observations
                       if observation["visual_confidence"] >= 0.8 and not observation["image_quality_issues"]
                       for item in observation["visible_damage"] if item["confidence"] >= 0.8}
    for region in sorted(reliable_damage & set(result["regions_visible_intact"])):
        result["visual_contradictions"].append(f"Conflicting damaged and intact observations for {region}; inspect source images.")
        result["requires_human_review"] = True
    result["image_observations"] = observations
    result["duplicate_images"] = duplicates
    return result
