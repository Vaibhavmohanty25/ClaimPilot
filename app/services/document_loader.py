from pathlib import Path
import fitz


def load_pdf(file_path: str) -> str:
    document = fitz.open(file_path)

    pages = []

    for page_number, page in enumerate(document, start=1):
        text = page.get_text()

        pages.append(
            f"""
--- PAGE {page_number} ---

{text}
"""
        )

    document.close()

    return "\n".join(pages)


def load_text_file(file_path: str) -> str:
    return Path(file_path).read_text(
        encoding="utf-8",
        errors="ignore",
    )


def load_document(file_path: str) -> str:
    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        return load_pdf(file_path)

    if suffix in {".txt", ".md"}:
        return load_text_file(file_path)

    raise ValueError(
        f"Unsupported document type: {suffix}"
    ) 