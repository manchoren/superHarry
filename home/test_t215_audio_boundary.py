from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase

from home.audio_boundary import (
    MAX_AUDIO_BYTES,
    MAX_FALLBACK_CHARS,
    AudioBoundaryError,
    plan_audio_deletion,
    prepare_stt_request,
    prepare_tts_request,
    run_local_stt,
    run_local_tts,
    prepare_audio_work,
    MAX_OPERATION_ID_CHARS,
)


class T215AudioBoundaryTests(SimpleTestCase):
    def test_stt_accepts_bounded_local_spanish_audio_and_stays_unavailable(self):
        request = prepare_stt_request(
            b"RIFF-local-fixture",
            content_type="audio/wav",
            language="spa",
            duration_seconds=12,
        )
        result = run_local_stt(request)
        self.assertEqual((result.status, result.source), ("UNAVAILABLE", "none"))
        self.assertFalse(result.trusted)

    def test_stt_rejects_unsupported_language_format_size_and_duration(self):
        kwargs = {"language": "spa", "duration_seconds": 1}
        with self.assertRaisesRegex(AudioBoundaryError, "language_unsupported"):
            prepare_stt_request(b"audio", content_type="audio/wav", language="fra", duration_seconds=1)
        with self.assertRaisesRegex(AudioBoundaryError, "format_unsupported"):
            prepare_stt_request(b"audio", content_type="audio/flac", **kwargs)
        with self.assertRaisesRegex(AudioBoundaryError, "audio_too_large"):
            prepare_stt_request(b"x" * (MAX_AUDIO_BYTES + 1), content_type="audio/wav", **kwargs)
        with self.assertRaisesRegex(AudioBoundaryError, "duration_out_of_bounds"):
            prepare_stt_request(b"audio", content_type="audio/wav", duration_seconds=0, language="spa")

    def test_tts_accepts_only_selected_spanish_voices_and_is_unavailable(self):
        request = prepare_tts_request(
            text="Respuesta local", language="spa", voice="es_AR-daniela-high"
        )
        result = run_local_tts(request)
        self.assertEqual(result.status, "UNAVAILABLE")
        with self.assertRaisesRegex(AudioBoundaryError, "voice_unsupported"):
            prepare_tts_request(text="Hola", language="spa", voice="cloud-voice")

    def test_text_fallback_is_bounded_and_explicitly_untrusted(self):
        request = prepare_tts_request(text="Hola", language="spa", voice="es_MX-ald-medium")
        result = run_local_tts(request, fallback_text="Respuesta textual")
        self.assertEqual((result.status, result.text), ("FALLBACK_TEXT", "Respuesta textual"))
        self.assertFalse(result.trusted)
        with self.assertRaisesRegex(AudioBoundaryError, "fallback_too_large"):
            run_local_stt(
                prepare_stt_request(b"audio", content_type="audio/ogg", language="eng", duration_seconds=1),
                fallback_text="x" * (MAX_FALLBACK_CHARS + 1),
            )

    def test_deletion_plan_is_timezone_normalized_and_does_not_delete(self):
        plan = plan_audio_deletion(
            "conversation/audio-1",
            delete_after=datetime(2026, 11, 16, 2, 0, tzinfo=timezone(timedelta(hours=-5))),
            processed_successfully=True,
        )
        self.assertEqual(plan.delete_after.tzinfo, timezone.utc)
        self.assertTrue(plan.retain_transcript)
        with self.assertRaisesRegex(AudioBoundaryError, "delete_after_must_be_timezone_aware"):
            plan_audio_deletion("audio-2", delete_after=datetime(2026, 11, 16, 2, 0), processed_successfully=True)

    def test_deletion_requires_success_and_audio_work_is_serialized_local_only(self):
        request = prepare_stt_request(b"audio", content_type="audio/wav", language="spa", duration_seconds=1)
        with self.assertRaisesRegex(AudioBoundaryError, "audio_processing_not_successful"):
            plan_audio_deletion("audio-3", delete_after=datetime.now(timezone.utc))
        plan = prepare_audio_work(request, operation_id="op-1", owner_id="user-1")
        self.assertEqual(plan.kind, "speech_to_text")
        self.assertTrue(plan.local_only and plan.serialized_heavy_work and plan.requires_shared_heavy_slot)
        with self.assertRaisesRegex(AudioBoundaryError, "operation_id_invalid"):
            prepare_audio_work(request, operation_id="x" * (MAX_OPERATION_ID_CHARS + 1), owner_id="user-1")

    def test_fallback_language_is_revalidated_for_bilingual_contract(self):
        request = prepare_stt_request(b"audio", content_type="audio/wav", language="eng", duration_seconds=1)
        self.assertEqual(run_local_stt(request, fallback_text="Use text").status, "FALLBACK_TEXT")
        with self.assertRaisesRegex(AudioBoundaryError, "language_unsupported"):
            from home.audio_boundary import unavailable_result
            unavailable_result(fallback_text="texto", language="fra")

    def test_fallback_and_plans_never_claim_real_audio_processing(self):
        request = prepare_stt_request(
            b"OggS-local-fixture", content_type="audio/ogg", language="eng", duration_seconds=2
        )
        result = run_local_stt(request, fallback_text="Text fallback")
        self.assertEqual(result.error_code, "audio_unavailable")
        self.assertNotIn("audio", result.source)
