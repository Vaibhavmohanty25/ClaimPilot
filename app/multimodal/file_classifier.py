from pathlib import Path


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp",
}

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
}

PDF_EXTENSIONS = {
    ".pdf",
}


def classify_file(
    file_path: str
) -> dict:
    path = Path(file_path)

    suffix = path.suffix.lower()

    if suffix in IMAGE_EXTENSIONS:
        return {
            "file_type": "image",
            "content_type": "image_document",
        }

    if suffix in TEXT_EXTENSIONS:
        return {
            "file_type": "text",
            "content_type": "digital_document",
        }

    if suffix in PDF_EXTENSIONS:
        return {
            "file_type": "pdf",
            "content_type": "pdf_document",
        }

    return {
        "file_type": "unknown",
        "content_type": "unsupported",
    }