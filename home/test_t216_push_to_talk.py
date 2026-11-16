from django.contrib.auth import get_user_model
import re
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse

from home.push_to_talk import LocalPushToTalk, PushToTalkError, MAX_AUDIO_BYTES


class PushToTalkContractTests(SimpleTestCase):
    def test_bounded_local_audio_and_text_fallback(self):
        manager = LocalPushToTalk()
        result = manager.start(owner_id=1, content_type="audio/webm", size=10, prefix=b"\x1a\x45\xdf\xa3", text_fallback="  hola\n mundo ")
        self.assertEqual(result.state, "unavailable")
        self.assertEqual(result.text_fallback, "  hola\n mundo ")
        self.assertEqual(manager.status(result.request_id, owner_id=1).state, "unavailable")
        self.assertEqual(manager.status(result.request_id, owner_id=2).state, "not_found")

    def test_rejects_unbounded_or_untrusted_audio(self):
        with self.assertRaises(PushToTalkError):
            LocalPushToTalk().start(owner_id=1, content_type="audio/webm", size=MAX_AUDIO_BYTES + 1, prefix=b"\x1a\x45\xdf\xa3")
        with self.assertRaises(PushToTalkError):
            LocalPushToTalk().start(owner_id=1, content_type="audio/webm", size=10, prefix=b"not-audio")
        with self.assertRaises(PushToTalkError):
            LocalPushToTalk().start(owner_id=1, content_type="audio/webm", size=10, prefix=b"RIFFxxxxWAVE")

    def test_text_fallback_does_not_stringify_untrusted_objects(self):
        result = LocalPushToTalk().start(owner_id=1, content_type="audio/ogg", size=4,
                                         prefix=b"OggS", text_fallback=object())
        self.assertEqual(result.text_fallback, "")

    def test_cancel_is_explicit_and_terminal(self):
        manager = LocalPushToTalk()
        result = manager.start(owner_id=1, content_type="audio/ogg", size=10, prefix=b"OggS")
        self.assertEqual(manager.cancel(result.request_id, owner_id=2).state, "not_found")
        self.assertEqual(manager.cancel(result.request_id, owner_id=1).state, "unavailable")


class PushToTalkViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="talker", password="pw")
        self.client = Client()
        self.client.force_login(self.user)

    def test_upload_requires_audio_and_is_local_unavailable(self):
        page = self.client.get(reverse("home"), secure=True)
        csrf = re.search(rb'name="csrfmiddlewaretoken" value="([^"]+)"', page.content).group(1).decode()
        request_kwargs = {"secure": True, "HTTP_HOST": "superharry.local", "HTTP_ORIGIN": "https://superharry.local", "HTTP_X_CSRFTOKEN": csrf}
        response = self.client.post(reverse("push-to-talk-start"), **request_kwargs)
        self.assertEqual(response.status_code, 400, response.content[:300])
        from django.core.files.uploadedfile import SimpleUploadedFile
        response = self.client.post(reverse("push-to-talk-start"), {"audio": SimpleUploadedFile("x.webm", b"\x1a\x45\xdf\xa3", content_type="audio/webm"), "text_fallback": "use text"}, **request_kwargs)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["state"], "unavailable")
        self.assertNotIn("provider", response.json())
        status = self.client.get(reverse("push-to-talk-status", args=[response.json()["request_id"]]), secure=True, HTTP_HOST="superharry.local")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["state"], "unavailable")

    def test_status_and_cancel_are_owner_scoped(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        request_kwargs = {"secure": True, "HTTP_HOST": "superharry.local", "HTTP_ORIGIN": "https://superharry.local"}
        response = self.client.post(reverse("push-to-talk-start"), {"audio": SimpleUploadedFile("x.webm", b"\x1a\x45\xdf\xa3", content_type="audio/webm")}, **request_kwargs)
        request_id = response.json()["request_id"]
        other = get_user_model().objects.create_user(username="other", password="pw")
        self.client.force_login(other)
        status = self.client.get(reverse("push-to-talk-status", args=[request_id]), **request_kwargs)
        self.assertEqual(status.status_code, 404)
        cancelled = self.client.post(reverse("push-to-talk-cancel", args=[request_id]), **request_kwargs)
        self.assertEqual(cancelled.status_code, 404)
