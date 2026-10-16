from pathlib import Path
import os
import shutil
import subprocess


_reader = None


def get_reader():
    global _reader

    if _reader is None:
        import easyocr
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

    if os.getenv('CLAIMPILOT_OCR_ENGINE', 'easyocr').strip().lower() == 'tesseract':
        executable = shutil.which('tesseract')
        if not executable:
            raise RuntimeError('Configured Tesseract OCR engine is not installed.')
        try:
            result = subprocess.run([executable, str(path), 'stdout', '-l', 'eng'],
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                timeout=60, check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            if result.returncode:
                raise RuntimeError('Document OCR failed. Please check the scan quality and try again.')
            return result.stdout.strip()
        except (subprocess.TimeoutExpired, OSError):
            # Never expose executable stderr or silently load another large model.
            raise RuntimeError('Document OCR could not finish. Please try a clearer or smaller scan.') from None

    reader = get_reader()

    results = reader.readtext(
        str(path),
        detail=0,
        paragraph=True,
        # CRAFT's default 2560-pixel canvas can exhaust a 1 GB CPU service.
        # Detection uses this bounded canvas; recognition keeps original crops.
        canvas_size=512,
    )

    return "\n".join(
        text.strip()
        for text in results
        if text.strip()
    )
