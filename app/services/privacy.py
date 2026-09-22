"""Sanitize the public boundary, including nested model/provider echoes."""
import os
import re


def safe_filename(value):
    name = str(value).replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"[^\w .()\-]", "_", name).strip(" .")[:150]
    return name or "upload"


def public_response(value, private_paths=()):
    if isinstance(value, dict):
        return {public_response(str(key), private_paths): public_response(item, private_paths)
                for key, item in value.items()
                if str(key).lower() not in {"path", "file_path", "image_path", "raw_response", "api_key", "groq_api_key"}}
    if isinstance(value, (list, tuple)):
        return [public_response(item, private_paths) for item in value]
    if not isinstance(value, str):
        return value
    secret = os.getenv("GROQ_API_KEY")
    if secret:
        value = value.replace(secret, "[redacted]")
    for path in sorted(private_paths, key=len, reverse=True):
        value = value.replace(path, "[private file]").replace(path.replace("\\", "/"), "[private file]")
    value = re.sub(r"(?:[A-Za-z]:[\\/]|\\\\)[^\n\r\"<>|]*", "[private file]", value)
    value = re.sub(r"(?<![\w:])/(?:[^\s/]+/)*[^\s,;\"<>]*", "[private file]", value)
    value = re.sub(r"\buploads[\\/][^\s,;\"<>]*", "[private file]", value, flags=re.I)
    value = re.sub(r"data:image/[^\s\"]+", "[image data]", value, flags=re.I)
    value = re.sub(r"gsk_[A-Za-z0-9]+", "[redacted]", value)
    return value
