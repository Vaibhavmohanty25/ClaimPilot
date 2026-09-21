from pathlib import Path
from tempfile import NamedTemporaryFile

import pymupdf
from PIL import Image

from app.services.ocr_service import (
    extract_text_from_image,
)

from app.multimodal.file_classifier import (
    classify_file,
)


MIN_NATIVE_TEXT_LENGTH = 40


def load_text_file(
    file_path: str
) -> dict:
    path = Path(file_path)

    text = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    return {
        "filename": path.name,
        "file_type": "text",
        "content_type": "digital_document",
        "extraction_method": "native_text",
        "pages": 1,
        "text": text,
    }


def extract_native_pdf_text(
    page
) -> str:
    text = page.get_text(
        "text"
    )

    return text.strip()


def page_needs_ocr(
    native_text: str
) -> bool:
    return len(
        native_text.strip()
    ) < MIN_NATIVE_TEXT_LENGTH


def render_page_to_image(
    page
) -> str:
    pix = page.get_pixmap(
        matrix=pymupdf.Matrix(
            2,
            2,
        )
    )

    temp_file = NamedTemporaryFile(
        suffix=".png",
        delete=False,
    )

    temp_path = temp_file.name

    temp_file.close()

    pix.save(
        temp_path
    )

    return temp_path


def load_pdf(
    file_path: str
) -> dict:
    path = Path(file_path)

    document = pymupdf.open(
        file_path
    )

    extracted_pages = []

    used_ocr = False

    try:
        for page_number, page in enumerate(
            document,
            start=1,
        ):
            native_text = (
                extract_native_pdf_text(
                    page
                )
            )

            if not page_needs_ocr(
                native_text
            ):
                page_text = native_text
                method = "native_text"

            else:
                image_path = (
                    render_page_to_image(
                        page
                    )
                )

                try:
                    page_text = (
                        extract_text_from_image(
                            image_path
                        )
                    )

                    method = "ocr"
                    used_ocr = True

                finally:
                    Path(
                        image_path
                    ).unlink(
                        missing_ok=True
                    )

            extracted_pages.append(
                {
                    "page_number": page_number,
                    "extraction_method": method,
                    "text": page_text,
                }
            )

    finally:
        document.close()

    combined_text = "\n\n".join(
        (
            f"--- PAGE "
            f"{page['page_number']} ---\n"
            f"{page['text']}"
        )
        for page in extracted_pages
    )

    content_type = (
        "scanned_or_mixed_pdf"
        if used_ocr
        else "digital_pdf"
    )

    extraction_method = (
        "mixed"
        if used_ocr
        else "native_text"
    )

    return {
        "filename": path.name,
        "file_type": "pdf",
        "content_type": content_type,
        "extraction_method": (
            extraction_method
        ),
        "pages": len(
            extracted_pages
        ),
        "page_details": (
            extracted_pages
        ),
        "text": combined_text,
    }


def load_image(
    file_path: str
) -> dict:
    path = Path(file_path)

    with Image.open(
        file_path
    ) as image:
        width, height = (
            image.size
        )

    text = (
        extract_text_from_image(
            file_path
        )
    )

    return {
        "filename": path.name,
        "file_type": "image",
        "content_type": "image_document",
        "extraction_method": "ocr",
        "pages": 1,
        "image_width": width,
        "image_height": height,
        "text": text,
    }


def load_document(
    file_path: str
) -> dict:
    classification = (
        classify_file(
            file_path
        )
    )

    file_type = (
        classification[
            "file_type"
        ]
    )

    if file_type == "text":
        return load_text_file(
            file_path
        )

    if file_type == "pdf":
        return load_pdf(
            file_path
        )

    if file_type == "image":
        return load_image(
            file_path
        )

    raise ValueError(
        (
            "Unsupported file type: "
            f"{Path(file_path).suffix}"
        )
    )