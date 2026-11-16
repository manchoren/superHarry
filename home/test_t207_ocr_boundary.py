from django.test import SimpleTestCase

from home.ocr_boundary import (
    MAX_FALLBACK_CHARS,
    OCRBoundaryError,
    INITIAL_ENGINE,
    ISOLATION_CONTRACT,
    prepare_ocr_request,
    run_local_ocr,
    select_engine,
)


def png(width=2, height=2):
    import struct

    return (
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + struct.pack(">II", width, height)
        + b"\x08\x02\x00\x00\x00"
        + b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


class OCRBoundaryTests(SimpleTestCase):
    def test_accepts_bounded_png_with_spanish_and_english(self):
        request = prepare_ocr_request(
            png(), content_type="image/png", languages=["spa", "eng"]
        )
        result = run_local_ocr(request)
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(result.source, "none")
        self.assertFalse(result.trusted)

    def test_engine_selection_is_explicit_and_no_automatic_alternative(self):
        self.assertEqual(select_engine(), INITIAL_ENGINE)
        self.assertEqual(select_engine("tesseract"), INITIAL_ENGINE)
        with self.assertRaisesRegex(OCRBoundaryError, "engine_not_approved"):
            select_engine("rapidocr")
        with self.assertRaisesRegex(OCRBoundaryError, "engine_unsupported"):
            select_engine("unknown")

    def test_request_records_engine_and_declares_isolation_contract(self):
        request = prepare_ocr_request(
            png(), content_type="image/png", languages=["spa"], engine="tesseract"
        )
        self.assertEqual(request.engine, "tesseract")
        self.assertTrue(ISOLATION_CONTRACT.network_disabled)
        self.assertTrue(ISOLATION_CONTRACT.sandbox_required)
        self.assertTrue(ISOLATION_CONTRACT.untrusted_output)

    def test_rejects_unsupported_format_language_and_mismatch(self):
        with self.assertRaisesRegex(OCRBoundaryError, "format_unsupported"):
            prepare_ocr_request(png(), content_type="application/pdf", languages=["spa"])
        with self.assertRaisesRegex(OCRBoundaryError, "language_unsupported"):
            prepare_ocr_request(png(), content_type="image/png", languages=["fra"])
        with self.assertRaisesRegex(OCRBoundaryError, "format_mismatch"):
            prepare_ocr_request(png(), content_type="image/jpeg", languages=["eng"])

    def test_rejects_oversized_input_before_any_engine_boundary(self):
        with self.assertRaisesRegex(OCRBoundaryError, "image_too_large"):
            prepare_ocr_request(b"x" * (10 * 1024 * 1024 + 1), content_type="image/png", languages=["spa"])

    def test_textual_fallback_is_bounded_and_explicitly_untrusted(self):
        request = prepare_ocr_request(png(), content_type="image/png", languages=["spa"])
        result = run_local_ocr(request, fallback_text="Salida de emergencia")
        self.assertEqual(result.status, "FALLBACK_TEXT")
        self.assertEqual(result.text, "Salida de emergencia")
        self.assertFalse(result.trusted)
        with self.assertRaisesRegex(OCRBoundaryError, "fallback_too_large"):
            run_local_ocr(request, fallback_text="x" * (MAX_FALLBACK_CHARS + 1))

    def test_no_fallback_does_not_synthesize_or_claim_ocr_output(self):
        request = prepare_ocr_request(png(), content_type="image/png", languages=["eng"])
        result = run_local_ocr(request)
        self.assertEqual((result.text, result.error_code), ("", "ocr_unavailable"))
