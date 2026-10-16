import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services import ocr_service


class TesseractOcrTests(unittest.TestCase):
    def test_tesseract_reads_document_without_initializing_neural_reader(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / 'scanned image.png'
            image.write_bytes(b'fixture')
            with patch.dict('os.environ', {'CLAIMPILOT_OCR_ENGINE': 'tesseract'}), \
                 patch('shutil.which', return_value='/usr/bin/tesseract'), \
                 patch('subprocess.run', return_value=subprocess.CompletedProcess([], 0, ' POLICE REPORT\n', '')) as run, \
                 patch.object(ocr_service, 'get_reader', side_effect=AssertionError('Neural reader must remain unloaded')):
                self.assertEqual(ocr_service.extract_text_from_image(str(image)), 'POLICE REPORT')
            self.assertEqual(run.call_args.args[0], ['/usr/bin/tesseract', str(image), 'stdout', '-l', 'eng'])
            self.assertEqual(run.call_args.kwargs['timeout'], 60)

    def test_tesseract_failure_does_not_leak_stderr_or_fall_back_to_large_model(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / 'scan.png'
            image.write_bytes(b'fixture')
            for result in (subprocess.CompletedProcess([], 1, '', 'private document text'), subprocess.TimeoutExpired('tesseract', 60)):
                kwargs = {'side_effect': result} if isinstance(result, Exception) else {'return_value': result}
                with self.subTest(result=type(result).__name__), patch.dict('os.environ', {'CLAIMPILOT_OCR_ENGINE': 'tesseract'}), \
                     patch('shutil.which', return_value='/usr/bin/tesseract'), patch('subprocess.run', **kwargs), \
                     patch.object(ocr_service, 'get_reader', side_effect=AssertionError('No memory-heavy fallback')):
                    with self.assertRaises(RuntimeError) as error:
                        ocr_service.extract_text_from_image(str(image))
                    self.assertNotIn('private document text', str(error.exception))

    def test_missing_configured_binary_fails_explicitly(self):
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / 'scan.png'
            image.write_bytes(b'fixture')
            with patch.dict('os.environ', {'CLAIMPILOT_OCR_ENGINE': 'tesseract'}), patch('shutil.which', return_value=None), \
                 patch.object(ocr_service, 'get_reader', side_effect=RuntimeError('Wrong engine selected')):
                with self.assertRaisesRegex(RuntimeError, 'not installed'):
                    ocr_service.extract_text_from_image(str(image))
