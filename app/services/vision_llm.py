import base64
import os
from pathlib import Path

from app.services.llm import client
from app.services.provider_retry import request_with_retry

# https://console.groq.com/docs/vision (verified 2026-09-22).
MAX_VISION_IMAGES = 3
SUPPORTED_IMAGE_SUFFIXES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                            ".png": "image/png", ".webp": "image/webp"}


def get_vision_model() -> str:
    model = os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.8-27b").strip()
    if not model:
        raise RuntimeError("GROQ_VISION_MODEL is required for damage-photo analysis.")
    return model


def encode_image_data_url(image_path: str) -> str:
    path = Path(image_path)
    mime_type = SUPPORTED_IMAGE_SUFFIXES.get(path.suffix.lower())
    if not mime_type:
        raise ValueError("Groq vision supports JPG, JPEG, PNG, and WEBP claim photos.")
    if not path.is_file():
        raise FileNotFoundError("Claim image was not found.")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def generate_vision_json(prompt: str, image_paths: list[str], max_retries: int = 3) -> str:
    if not 1 <= len(image_paths) <= MAX_VISION_IMAGES:
        raise ValueError("Vision accepts between 1 and 3 images per claim request.")
    model = get_vision_model()
    content = [{"type": "text", "text": prompt}]
    content.extend({"type": "image_url", "image_url": {"url": encode_image_data_url(path)}} for path in image_paths)
    return request_with_retry(
        lambda: client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": content}],
            temperature=0.1, response_format={"type": "json_object"},
        ), model=model, stage="vision_llm", max_attempts=max_retries, image_count=len(image_paths),
    )
