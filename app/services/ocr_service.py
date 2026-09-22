from pathlib import Path

import easyocr


_reader = None


def get_reader():
    global _reader

    if _reader is None:
        _reader = easyocr.Reader(
            ["en"],
            gpu=False,
        )

    return _reader


def extract_text_from_image(
    image_path: str
) -> str:
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(
            "Image not found."
        )

    reader = get_reader()

    results = reader.readtext(
        str(path),
        detail=0,
        paragraph=True,
    )

    return "\n".join(
        text.strip()
        for text in results
        if text.strip()
    )
