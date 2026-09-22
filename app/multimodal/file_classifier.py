from pathlib import Path

from PIL import Image, ImageStat


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

DOCUMENT_IMAGE_HINTS = {
    "claim",
    "form",
    "estimate",
    "invoice",
    "quotation",
    "quote",
    "garage",
    "workshop",
    "police",
    "report",
    "receipt",
}


def classify_file(
    file_path: str
) -> dict:
    path = Path(file_path)

    suffix = path.suffix.lower()

    if suffix in IMAGE_EXTENSIONS:
        name_words = set(
            path.stem.lower().replace("-", "_").split("_")
        )

        result = {"file_type": "image", "content_type": "unknown_image",
                  "classification_confidence": 0.0, "classification_method": "pixel_layout"}
        try:
            with Image.open(path) as image:
                image.thumbnail((600, 800))
                rgb = image.convert("RGB")
                gray = rgb.convert("L")
                histogram = gray.histogram()
                pixels = gray.width * gray.height
                white_fraction = sum(histogram[220:]) / pixels
                dark_fraction = sum(histogram[:140]) / pixels
                row_ink = []
                for y in range(gray.height):
                    row = gray.crop((0, y, gray.width, y + 1)).histogram()
                    row_ink.append(sum(row[:140]) / gray.width > 0.015)
                bands = sum(ink and (i == 0 or not row_ink[i - 1]) for i, ink in enumerate(row_ink))
                paper_layout = white_fraction > 0.65 and 0.002 < dark_fraction < 0.3 and bands >= 4
                photographic = gray.entropy() > 5 and white_fraction < 0.5 and max(ImageStat.Stat(rgb).stddev) > 25
            if paper_layout:
                # OCR is gated by document layout, never by an accident filename.
                from app.services.ocr_service import extract_text_from_image
                text = extract_text_from_image(str(path))
                words = text.split()
                if len(words) >= 10 and sum(c.isalpha() for c in text) >= 40:
                    result.update(content_type="document_image", classification_confidence=0.9,
                                  classification_method="layout_and_ocr")
                else:
                    result["classification_confidence"] = 0.4
            elif photographic:
                result.update(content_type="damage_photo", classification_confidence=0.75)
            # Filename can only modestly reinforce pixel/OCR evidence.
            if result["content_type"] == "document_image" and name_words & DOCUMENT_IMAGE_HINTS:
                result["classification_confidence"] += 0.03
        except (OSError, ValueError, RuntimeError):
            pass
        return result

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
