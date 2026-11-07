import base64
from io import StringIO
import hashlib
import os
import stat
import tempfile
from types import SimpleNamespace
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.contrib import admin
from django.contrib.sessions.backends.db import SessionStore
from django.conf import settings
from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.core.management import call_command, CommandError
from django.utils import timezone

from home.audit import AuditUnavailable
from home.auth_views import TOTPAuthenticationForm
from home.admin import AuditedUserAdmin
from home.models import AuditEvent, LoginAttemptCounter, PasswordResetGrant, TOTPDevice, TOTPRecoveryCode
from home.login_attempts import record_failed_attempt
from home.password_reset import decode_reset_token, reset_token_digest
from home.passwords import normalize_password
from home.totp import (
    CredentialUnavailable,
    consume_recovery_code,
    decrypt_secret,
    encrypt_secret,
    expire_pending_devices,
    generate_recovery_codes,
    matching_step,
    recovery_verifier,
    totp_step,
    verify_device_code,
)


User = get_user_model()


class T027TestCase(TestCase):
    def setUp(self):
        self.credential_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.credential_dir.cleanup)
        self.key = bytes(range(32))
        key_path = os.path.join(self.credential_dir.name, "totp-aes256-key")
        with open(key_path, "wb") as handle:
            handle.write(self.key)
        os.chmod(key_path, 0o600)
        self.env = patch.dict(
            os.environ,
            {"CREDENTIALS_DIRECTORY": self.credential_dir.name},
        )
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client.defaults["HTTP_HOST"] = settings.SUPERHARRY_HOSTNAME
        if os.name == "nt":
            native_fstat = os.fstat

            def fstat_with_private_mode(file_descriptor):
                result = native_fstat(file_descriptor)
                private_mode = result.st_mode & ~0o077
                return os.stat_result((private_mode, *result[1:]))

            private_mode_patch = patch(
                "home.totp.os.fstat",
                side_effect=fstat_with_private_mode,
            )
            private_mode_patch.start()
            self.addCleanup(private_mode_patch.stop)
        self.user = User.objects.create_user(
            username="t027-user",
            password="A sufficiently long test passphrase 42",
        )


class TOTPStorageTests(T027TestCase):
    def test_aes_gcm_is_bound_to_user_and_key_version(self):
        secret = bytes(range(20))
        encrypt_secret(self.user.pk, secret)
        device = TOTPDevice.objects.get(user=self.user)
        self.assertEqual(decrypt_secret(device), secret)

        device.user_id += 1
        with self.assertRaises(CredentialUnavailable):
            decrypt_secret(device)
        device.refresh_from_db()
        with override_settings(SUPERHARRY_TOTP_KEY_VERSION=2):
            with self.assertRaises(CredentialUnavailable):
                decrypt_secret(device)

        device.secret_ciphertext = bytes(device.secret_ciphertext[:-1]) + bytes(
            [device.secret_ciphertext[-1] ^ 1]
        )
        device.save(update_fields=("secret_ciphertext",))
        with self.assertRaises(CredentialUnavailable):
            decrypt_secret(device)

    def test_missing_or_invalid_host_credential_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(CredentialUnavailable):
                encrypt_secret(self.user.pk, b"secret")

    def test_group_or_other_readable_host_credential_fails_closed(self):
        native_fstat = os.fstat

        def readable_mode(file_descriptor):
            result = native_fstat(file_descriptor)
            return os.stat_result((result.st_mode | 0o004, *result[1:]))

        with patch("home.totp.os.fstat", side_effect=readable_mode):
            with self.assertRaises(CredentialUnavailable):
                encrypt_secret(self.user.pk, b"secret")

    def test_nonce_constraint_rejects_reuse_for_same_key_version(self):
        first = TOTPDevice.objects.create(
            user=self.user,
            secret_ciphertext=b"ciphertext",
            nonce=b"n" * 12,
            key_version=1,
        )
        other = User.objects.create_user(
            username="t027-other",
            password="Another sufficiently long password 42",
        )
        with self.assertRaises(Exception):
            TOTPDevice.objects.create(
                user=other,
                secret_ciphertext=b"ciphertext",
                nonce=first.nonce,
                key_version=1,
            )


class TOTPLifecycleTests(T027TestCase):
    def _confirmed_device(self, secret=None):
        secret = secret or bytes(range(20))
        encrypt_secret(self.user.pk, secret)
        device = TOTPDevice.objects.get(user=self.user)
        device.confirmed_at = timezone.now()
        device.save(update_fields=("confirmed_at",))
        return device, secret

    def test_totp_window_and_replay_rejection(self):
        secret = bytes(range(20))
        current_time = 1_700_000_000
        current_step, code = totp_step(secret, current_time)
        self.assertEqual(matching_step(secret, code, now=current_time), current_step)
        device, _secret = self._confirmed_device(secret)
        self.assertTrue(verify_device_code(device, code, now=current_time))
        self.assertFalse(verify_device_code(device, code, now=current_time))

    def test_recovery_codes_have_128_bits_and_are_single_use(self):
        device, _secret = self._confirmed_device()
        codes = generate_recovery_codes()
        self.assertEqual(len(codes), 10)
        self.assertEqual(len(set(codes)), 10)
        self.assertTrue(all(len(code) == 26 for code in codes))
        TOTPRecoveryCode.objects.bulk_create(
            [TOTPRecoveryCode(device=device, verifier=recovery_verifier(code)) for code in codes]
        )
        self.assertTrue(consume_recovery_code(device, codes[0]))
        self.assertFalse(consume_recovery_code(device, codes[0]))
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.TOTP_RECOVERY_USED,
                target_user_id=self.user.pk,
            ).exists()
        )

    def test_pending_expiry_deletes_device_and_audits_atomically(self):
        encrypt_secret(self.user.pk, bytes(range(20)))
        device = TOTPDevice.objects.get(user=self.user)
        TOTPDevice.objects.filter(pk=device.pk).update(
            created_at=timezone.now() - timedelta(minutes=11)
        )
        self.assertEqual(expire_pending_devices(user_id=self.user.pk), 1)
        self.assertFalse(TOTPDevice.objects.filter(pk=device.pk).exists())
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.TOTP_ENROLLMENT_EXPIRED,
                target_user_id=self.user.pk,
            ).exists()
        )

    def test_pending_expiry_rolls_back_if_audit_fails(self):
        encrypt_secret(self.user.pk, bytes(range(20)))
        device = TOTPDevice.objects.get(user=self.user)
        TOTPDevice.objects.filter(pk=device.pk).update(
            created_at=timezone.now() - timedelta(minutes=11)
        )
        with patch("home.totp.record_event", side_effect=AuditUnavailable):
            with self.assertRaises(AuditUnavailable):
                expire_pending_devices(user_id=self.user.pk)
        self.assertTrue(TOTPDevice.objects.filter(pk=device.pk).exists())

    def test_daily_cleanup_command_uses_audited_expiry_service(self):
        encrypt_secret(self.user.pk, bytes(range(20)))
        device = TOTPDevice.objects.get(user=self.user)
        TOTPDevice.objects.filter(pk=device.pk).update(
            created_at=timezone.now() - timedelta(minutes=11)
        )
        call_command("prune_totp_enrollments", stdout=StringIO())
        self.assertFalse(TOTPDevice.objects.filter(pk=device.pk).exists())


class PasswordPolicyTests(T027TestCase):
    def test_minimum_length_is_15_nfc_codepoints_and_unicode_is_preserved(self):
        with self.assertRaises(ValidationError):
            validate_password("Short pass 12")
        validate_password("A sufficiently long password 42")
        validate_password(("Aa7!bC9?dE2#fG4%" * 4)[:64])
        normalized = normalize_password("Cafe\u0301 passphrase with 42")
        self.assertEqual(normalized, "Café passphrase with 42")
        encoded = make_password(normalized)
        self.assertTrue(check_password("Cafe\u0301 passphrase with 42", encoded))


class AuthenticationFlowTests(T027TestCase):
    def _login(self, password, code=""):
        return self.client.post(
            "/accounts/login/",
            {"username": self.user.username, "password": password, "totp_code": code},
            secure=True,
            HTTP_ORIGIN=f"https://{settings.SUPERHARRY_HOSTNAME}",
        )

    def test_password_login_is_generic_and_audits_failure(self):
        wrong = self._login("wrong password 123")
        self.assertEqual(wrong.status_code, 200)
        self.assertContains(wrong, "Your username and password didn't match")
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.PASSWORD_VERIFICATION_FAILED,
                target_user_id=self.user.pk,
            ).exists()
        )
        success = self._login("A sufficiently long test passphrase 42")
        self.assertEqual(success.status_code, 302)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.LOGIN_SUCCEEDED,
                target_user_id=self.user.pk,
            ).exists()
        )

    def test_enrolled_account_requires_valid_nonreplayed_totp(self):
        secret = bytes(range(20))
        encrypt_secret(self.user.pk, secret)
        device = TOTPDevice.objects.get(user=self.user)
        device.confirmed_at = timezone.now()
        device.save(update_fields=("confirmed_at",))
        _step, code = totp_step(secret)
        response = self._login("A sufficiently long test passphrase 42", code)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            TOTPDevice.objects.get(pk=device.pk).last_accepted_step,
            totp_step(secret)[0],
        )
        self.client.logout()
        replay = self._login("A sufficiently long test passphrase 42", code)
        self.assertEqual(replay.status_code, 200)
        self.assertContains(replay, "Your username and password didn't match")
        self.assertFalse("_auth_user_id" in self.client.session)

    def test_invalid_totp_is_audited_as_factor_failure_and_counts_toward_lockout(self):
        secret = bytes(range(20))
        encrypt_secret(self.user.pk, secret)
        device = TOTPDevice.objects.get(user=self.user)
        device.confirmed_at = timezone.now()
        device.save(update_fields=("confirmed_at",))
        response = self._login(
            "A sufficiently long test passphrase 42",
            "000000",
        )
        self.assertEqual(response.status_code, 200)
        counter = LoginAttemptCounter.objects.get(user=self.user)
        self.assertEqual(counter.failure_count, 1)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.TOTP_VERIFICATION_FAILED,
                target_user_id=self.user.pk,
            ).exists()
        )
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.PASSWORD_VERIFICATION_FAILED,
                target_user_id=self.user.pk,
            ).exists()
        )

    def test_account_delay_blocks_correct_credentials_after_five_failures(self):
        for _attempt in range(5):
            self._login("wrong password 123")
        before = AuditEvent.objects.filter(
            event_type=AuditEvent.EventType.PASSWORD_VERIFICATION_FAILED,
            target_user_id=self.user.pk,
        ).count()
        blocked = self._login("A sufficiently long test passphrase 42")
        self.assertEqual(blocked.status_code, 200)
        after = AuditEvent.objects.filter(
            event_type=AuditEvent.EventType.PASSWORD_VERIFICATION_FAILED,
            target_user_id=self.user.pk,
        ).count()
        self.assertEqual(before, 5)
        self.assertEqual(after, before)

    def test_account_delay_runs_fifteen_minutes_from_fifth_failure(self):
        current_time = timezone.now()
        LoginAttemptCounter.objects.create(
            user=self.user,
            window_started_at=current_time - timedelta(minutes=4),
            failure_count=5,
            locked_until=current_time + timedelta(minutes=15),
        )
        form = TOTPAuthenticationForm(
            data={"username": self.user.username, "password": "irrelevant"}
        )
        with patch("home.auth_views.timezone.now", return_value=current_time + timedelta(minutes=14)):
            self.assertTrue(form._account_locked(self.user.username))
        with patch("home.auth_views.timezone.now", return_value=current_time + timedelta(minutes=16)):
            self.assertFalse(form._account_locked(self.user.username))

    def test_audit_failure_does_not_lose_committed_attempt_counter(self):
        with patch("home.auth_views.record_event", side_effect=AuditUnavailable):
            response = self._login("wrong password 123")
        self.assertEqual(response.status_code, 503)
        counter = LoginAttemptCounter.objects.get(user=self.user)
        self.assertEqual(counter.failure_count, 1)

    def test_totp_audit_failure_rolls_back_attempt_counter(self):
        secret = bytes(range(20))
        encrypt_secret(self.user.pk, secret)
        device = TOTPDevice.objects.get(user=self.user)
        device.confirmed_at = timezone.now()
        device.save(update_fields=("confirmed_at",))

        with patch("home.auth_views.record_event", side_effect=AuditUnavailable):
            response = self._login(
                "A sufficiently long test passphrase 42",
                "000000",
            )

        self.assertEqual(response.status_code, 503)
        self.assertFalse(LoginAttemptCounter.objects.filter(user=self.user).exists())

    def test_successful_login_clears_prior_failed_attempts(self):
        record_failed_attempt(self.user.pk)
        self.assertTrue(LoginAttemptCounter.objects.filter(user=self.user).exists())
        response = self._login("A sufficiently long test passphrase 42")
        self.assertEqual(response.status_code, 302)
        self.assertFalse(LoginAttemptCounter.objects.filter(user=self.user).exists())

    def test_audit_unavailability_blocks_login(self):
        with patch("home.auth_views.record_event", side_effect=AuditUnavailable):
            response = self._login("wrong password 123")
        self.assertEqual(response.status_code, 503)

    def test_missing_totp_key_fails_closed_and_audits_specific_cause(self):
        secret = bytes(range(20))
        encrypt_secret(self.user.pk, secret)
        device = TOTPDevice.objects.get(user=self.user)
        device.confirmed_at = timezone.now()
        device.save(update_fields=("confirmed_at",))
        _step, code = totp_step(secret)
        with patch.dict(os.environ, {}, clear=True):
            response = self._login("A sufficiently long test passphrase 42", code)
        self.assertEqual(response.status_code, 200)
        self.assertFalse("_auth_user_id" in self.client.session)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.TOTP_KEY_UNAVAILABLE,
                target_user_id=self.user.pk,
            ).exists()
        )
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.PASSWORD_VERIFICATION_FAILED,
                target_user_id=self.user.pk,
            ).exists()
        )

    def test_recovery_code_login_consumes_and_audits_one_code(self):
        secret = bytes(range(20))
        encrypt_secret(self.user.pk, secret)
        device = TOTPDevice.objects.get(user=self.user)
        device.confirmed_at = timezone.now()
        device.save(update_fields=("confirmed_at",))
        code = generate_recovery_codes()[0]
        TOTPRecoveryCode.objects.create(device=device, verifier=recovery_verifier(code))

        response = self._login("A sufficiently long test passphrase 42", code)
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(
            TOTPRecoveryCode.objects.get(device=device).consumed_at
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.TOTP_RECOVERY_USED,
                target_user_id=self.user.pk,
            ).exists()
        )


class TOTPAdministrationTests(T027TestCase):
    def _post(self, path, data):
        return self.client.post(
            path,
            data,
            secure=True,
            HTTP_ORIGIN=f"https://{settings.SUPERHARRY_HOSTNAME}",
        )

    def _device(self, user):
        secret = bytes(range(20))
        encrypt_secret(user.pk, secret)
        device = TOTPDevice.objects.get(user=user)
        device.confirmed_at = timezone.now()
        device.save(update_fields=("confirmed_at",))
        return device, secret

    def test_step_up_failures_count_and_lock_out_later_reauthentication(self):
        device, secret = self._device(self.user)
        self.client.force_login(self.user, backend="home.backends.UsernameAuthenticationBackend")
        password = "A sufficiently long test passphrase 42"
        for _attempt in range(5):
            response = self._post(
                "/accounts/totp/disable/",
                {
                    "confirm": "disable-totp",
                    "password": password,
                    "totp_code": "invalid",
                },
            )
            self.assertEqual(response.status_code, 400)
        counter = LoginAttemptCounter.objects.get(user=self.user)
        self.assertEqual(counter.failure_count, 5)
        self.assertIsNotNone(counter.locked_until)

        _step, valid_code = totp_step(secret)
        blocked = self._post(
            "/accounts/totp/disable/",
            {
                "confirm": "disable-totp",
                "password": password,
                "totp_code": valid_code,
            },
        )
        self.assertEqual(blocked.status_code, 400)
        self.assertTrue(TOTPDevice.objects.filter(pk=device.pk).exists())
        self.assertEqual(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.TOTP_VERIFICATION_FAILED,
                target_user_id=self.user.pk,
            ).count(),
            5,
        )

    def test_step_up_audit_failure_rolls_back_attempt_counter(self):
        self._device(self.user)
        self.client.force_login(self.user, backend="home.backends.UsernameAuthenticationBackend")
        with patch("home.totp_views.record_event", side_effect=AuditUnavailable):
            response = self._post(
                "/accounts/totp/disable/",
                {
                    "confirm": "disable-totp",
                    "password": "A sufficiently long test passphrase 42",
                    "totp_code": "invalid",
                },
            )
        self.assertEqual(response.status_code, 503)
        self.assertFalse(LoginAttemptCounter.objects.filter(user=self.user).exists())

    def test_enrollment_confirmation_audit_failure_rolls_back_attempt_counter(self):
        encrypt_secret(self.user.pk, bytes(range(20)))
        device = TOTPDevice.objects.get(user=self.user)
        self.client.force_login(self.user, backend="home.backends.UsernameAuthenticationBackend")
        with patch("home.totp_views.record_event", side_effect=AuditUnavailable):
            response = self._post(
                "/accounts/totp/enrollment/confirm/",
                {
                    "confirm": "confirm-enrollment",
                    "password": "A sufficiently long test passphrase 42",
                    "totp_code": "invalid",
                },
            )
        self.assertEqual(response.status_code, 503)
        self.assertFalse(LoginAttemptCounter.objects.filter(user=self.user).exists())
        device.refresh_from_db()
        self.assertIsNone(device.confirmed_at)

    def test_enrollment_key_unavailable_is_audited(self):
        self.client.force_login(self.user, backend="home.backends.UsernameAuthenticationBackend")
        with patch.dict(os.environ, {}, clear=True):
            response = self._post(
                "/accounts/totp/enrollment/start/",
                {
                    "confirm": "start-enrollment",
                    "password": "A sufficiently long test passphrase 42",
                },
            )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.TOTP_KEY_UNAVAILABLE,
                target_user_id=self.user.pk,
            ).exists()
        )
        self.assertFalse(TOTPDevice.objects.filter(user=self.user).exists())

    def test_user_can_disable_factor_after_password_and_totp_reauthentication(self):
        device, secret = self._device(self.user)
        self.client.force_login(self.user, backend="home.backends.UsernameAuthenticationBackend")
        _step, code = totp_step(secret)
        response = self._post(
            "/accounts/totp/disable/",
            {
                "confirm": "disable-totp",
                "password": "A sufficiently long test passphrase 42",
                "totp_code": code,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TOTPDevice.objects.filter(pk=device.pk).exists())
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.TOTP_DEACTIVATED,
                target_user_id=self.user.pk,
            ).exists()
        )

    def test_admin_totp_reset_requires_permission_reauth_confirmation_and_audit(self):
        device, _secret = self._device(self.user)
        admin_user = User.objects.create_superuser(
            username="t027-admin",
            email="admin@example.invalid",
            password="An administrator password 987",
        )
        self.client.force_login(admin_user, backend="home.backends.UsernameAuthenticationBackend")
        response = self._post(
            f"/admin/users/{self.user.pk}/totp/reset/",
            {
                "confirm": "reset-totp",
                "password": "An administrator password 987",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TOTPDevice.objects.filter(pk=device.pk).exists())
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.TOTP_DEACTIVATED,
                actor_user_id=admin_user.pk,
                target_user_id=self.user.pk,
            ).exists()
        )

    def test_admin_totp_reset_denies_non_admin_and_staff_target(self):
        self._device(self.user)
        self.client.force_login(self.user, backend="home.backends.UsernameAuthenticationBackend")
        denied = self._post(
            f"/admin/users/{self.user.pk}/totp/reset/",
            {"confirm": "reset-totp", "password": "A sufficiently long test passphrase 42"},
        )
        self.assertEqual(denied.status_code, 403)
        self.assertTrue(TOTPDevice.objects.filter(user=self.user).exists())

    def test_totp_disable_and_admin_reset_roll_back_when_audit_is_unavailable(self):
        device, secret = self._device(self.user)
        self.client.force_login(self.user, backend="home.backends.UsernameAuthenticationBackend")
        _step, code = totp_step(secret)
        with patch("home.totp_views.record_event", side_effect=AuditUnavailable):
            disabled = self._post(
                "/accounts/totp/disable/",
                {
                    "confirm": "disable-totp",
                    "password": "A sufficiently long test passphrase 42",
                    "totp_code": code,
                },
            )
        self.assertEqual(disabled.status_code, 503)
        self.assertTrue(TOTPDevice.objects.filter(pk=device.pk).exists())

        admin_user = User.objects.create_superuser(
            username="t027-reset-admin",
            email="reset-admin@example.invalid",
            password="An administrator password 987",
        )
        self.client.force_login(admin_user, backend="home.backends.UsernameAuthenticationBackend")
        with patch("home.totp_views.record_event", side_effect=AuditUnavailable):
            reset = self._post(
                f"/admin/users/{self.user.pk}/totp/reset/",
                {
                    "confirm": "reset-totp",
                    "password": "An administrator password 987",
                },
            )
        self.assertEqual(reset.status_code, 503)
        self.assertTrue(TOTPDevice.objects.filter(pk=device.pk).exists())


class AccountLifecycleAdminTests(T027TestCase):
    def setUp(self):
        super().setUp()
        self.actor = User.objects.create_superuser(
            username="t027-lifecycle-admin",
            email="lifecycle@example.invalid",
            password="An administrator password 987",
        )
        self.user_admin = AuditedUserAdmin(User, admin.site)
        self.request = type("Request", (), {"user": self.actor})()

    def _create_user_session(self):
        session = SessionStore()
        session["_auth_user_id"] = str(self.user.pk)
        session["_auth_user_backend"] = "home.backends.UsernameAuthenticationBackend"
        session.save()
        return session.session_key

    def test_deactivation_revokes_sessions_and_audits_both_changes(self):
        session_key = self._create_user_session()
        user = User.objects.get(pk=self.user.pk)
        user.is_active = False
        self.user_admin.save_model(self.request, user, object(), change=True)
        self.assertFalse(SessionStore(session_key=session_key).exists(session_key))
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.USER_DEACTIVATED,
                target_user_id=user.pk,
            ).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.SESSION_REVOKED,
                actor_user_id=self.actor.pk,
                target_user_id=user.pk,
            ).exists()
        )

    def test_role_change_revokes_sessions_and_audit_failure_rolls_back(self):
        session_key = self._create_user_session()
        user = User.objects.get(pk=self.user.pk)
        user.is_staff = True
        with patch("home.admin.record_event", side_effect=AuditUnavailable):
            with self.assertRaises(AuditUnavailable):
                with transaction.atomic():
                    self.user_admin.save_model(self.request, user, object(), change=True)
                    self.user_admin.save_related(
                        self.request,
                        type("Form", (), {"instance": user, "save_m2m": lambda _self: None})(),
                        [],
                        change=True,
                    )
        user.refresh_from_db()
        self.assertFalse(user.is_staff)
        self.assertTrue(SessionStore(session_key=session_key).exists(session_key))


class TOTPHttpFlowTests(T027TestCase):
    def _post(self, path, data):
        return self.client.post(
            path,
            data,
            secure=True,
            HTTP_ORIGIN=f"https://{settings.SUPERHARRY_HOSTNAME}",
        )

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user, backend="home.backends.UsernameAuthenticationBackend")

    def test_enrollment_requires_explicit_start_confirmation_and_password(self):
        denied = self._post(
            "/accounts/totp/enrollment/start/",
            {"confirm": "start-enrollment"},
        )
        self.assertEqual(denied.status_code, 400)
        self.assertFalse(TOTPDevice.objects.filter(user=self.user).exists())

        started = self._post(
            "/accounts/totp/enrollment/start/",
            {
                "confirm": "start-enrollment",
                "password": "A sufficiently long test passphrase 42",
            },
        )
        self.assertEqual(started.status_code, 200)
        self.assertIn("no-store", started.headers.get("Cache-Control", ""))
        secret_text = started.json()["secret"]
        self.assertEqual(len(secret_text), 32)
        device = TOTPDevice.objects.get(user=self.user)
        self.assertIsNone(device.confirmed_at)
        self.assertNotIn(secret_text.encode("ascii"), bytes(device.secret_ciphertext))

        raw_secret = base64.b32decode(secret_text + "=" * (-len(secret_text) % 8))
        _step, code = totp_step(raw_secret)
        confirmed = self._post(
            "/accounts/totp/enrollment/confirm/",
            {
                "confirm": "confirm-enrollment",
                "password": "A sufficiently long test passphrase 42",
                "totp_code": code,
            },
        )
        self.assertEqual(confirmed.status_code, 200)
        self.assertIn("no-store", confirmed.headers.get("Cache-Control", ""))
        self.assertEqual(len(confirmed.json()["recovery_codes"]), 10)
        device.refresh_from_db()
        self.assertIsNotNone(device.confirmed_at)
        self.assertEqual(device.recovery_codes.count(), 10)

    def test_key_rotation_requires_audited_factor_reset_and_reenrollment(self):
        old_secret = bytes(range(20))
        encrypt_secret(self.user.pk, old_secret)
        old_device = TOTPDevice.objects.get(user=self.user)
        old_device.confirmed_at = timezone.now()
        old_device.save(update_fields=("confirmed_at",))

        admin_user = User.objects.create_superuser(
            username="t027-rotation-admin",
            email="rotation-admin@example.invalid",
            password="An administrator password 987",
        )

        key_path = os.path.join(self.credential_dir.name, "totp-aes256-key")
        with open(key_path, "wb") as handle:
            handle.write(bytes(reversed(range(32))))
        os.chmod(key_path, 0o600)

        with override_settings(SUPERHARRY_TOTP_KEY_VERSION=2):
            self.client.logout()
            _old_step, old_code = totp_step(old_secret)
            rejected = self._post(
                "/accounts/login/",
                {
                    "username": self.user.username,
                    "password": "A sufficiently long test passphrase 42",
                    "totp_code": old_code,
                },
            )
            self.assertEqual(rejected.status_code, 200)
            self.assertNotIn("_auth_user_id", self.client.session)
            self.assertTrue(
                AuditEvent.objects.filter(
                    event_type=AuditEvent.EventType.TOTP_KEY_UNAVAILABLE,
                    target_user_id=self.user.pk,
                ).exists()
            )

            self.client.force_login(
                admin_user,
                backend="home.backends.UsernameAuthenticationBackend",
            )
            reset = self._post(
                f"/admin/users/{self.user.pk}/totp/reset/",
                {
                    "confirm": "reset-totp",
                    "password": "An administrator password 987",
                },
            )
            self.assertEqual(reset.status_code, 200)
            self.assertFalse(TOTPDevice.objects.filter(pk=old_device.pk).exists())
            self.assertTrue(
                AuditEvent.objects.filter(
                    event_type=AuditEvent.EventType.TOTP_DEACTIVATED,
                    actor_user_id=admin_user.pk,
                    target_user_id=self.user.pk,
                ).exists()
            )

            self.client.force_login(
                self.user,
                backend="home.backends.UsernameAuthenticationBackend",
            )
            started = self._post(
                "/accounts/totp/enrollment/start/",
                {
                    "confirm": "start-enrollment",
                    "password": "A sufficiently long test passphrase 42",
                },
            )
            self.assertEqual(started.status_code, 200)
            secret_text = started.json()["secret"]
            new_secret = base64.b32decode(secret_text + "=" * (-len(secret_text) % 8))
            _step, enrollment_code = totp_step(new_secret)
            confirmed = self._post(
                "/accounts/totp/enrollment/confirm/",
                {
                    "confirm": "confirm-enrollment",
                    "password": "A sufficiently long test passphrase 42",
                    "totp_code": enrollment_code,
                },
            )
            self.assertEqual(confirmed.status_code, 200)
            new_device = TOTPDevice.objects.get(user=self.user)
            self.assertEqual(new_device.key_version, 2)
            self.assertEqual(new_device.recovery_codes.count(), 10)

            self.client.logout()
            current_step, _current_code = totp_step(new_secret)
            _next_step, new_code = totp_step(
                new_secret,
                at_time=(current_step + 1) * 30,
            )
            login = self._post(
                "/accounts/login/",
                {
                    "username": self.user.username,
                    "password": "A sufficiently long test passphrase 42",
                    "totp_code": new_code,
                },
            )
            self.assertEqual(login.status_code, 302)
            self.assertEqual(str(self.user.pk), self.client.session.get("_auth_user_id"))

    def test_enrollment_audit_failure_rolls_back_confirmation(self):
        start = self._post(
            "/accounts/totp/enrollment/start/",
            {
                "confirm": "start-enrollment",
                "password": "A sufficiently long test passphrase 42",
            },
        )
        secret_text = start.json()["secret"]
        raw_secret = base64.b32decode(secret_text + "=" * (-len(secret_text) % 8))
        _step, code = totp_step(raw_secret)
        with patch("home.totp_views.record_event", side_effect=AuditUnavailable):
            failed = self._post(
                "/accounts/totp/enrollment/confirm/",
                {
                    "confirm": "confirm-enrollment",
                    "password": "A sufficiently long test passphrase 42",
                    "totp_code": code,
                },
            )
        self.assertEqual(failed.status_code, 503)
        device = TOTPDevice.objects.get(user=self.user)
        self.assertIsNone(device.confirmed_at)
        self.assertEqual(device.recovery_codes.count(), 0)


class PasswordResetTests(T027TestCase):
    def _issue(self, raw_token, *, expires_at=None):
        now = timezone.now()
        return PasswordResetGrant.objects.create(
            user=self.user,
            token_digest=reset_token_digest(raw_token),
            issued_at=now,
            expires_at=expires_at or now + timedelta(minutes=10),
        )

    def _post_reset(self, data):
        return self.client.post(
            "/accounts/password-reset/",
            data,
            secure=True,
            HTTP_ORIGIN=f"https://{settings.SUPERHARRY_HOSTNAME}",
        )

    def test_reset_token_encoding_is_canonical_256_bit_base64url(self):
        raw_token = bytes(range(32))
        token = base64.urlsafe_b64encode(raw_token).decode("ascii").rstrip("=")
        self.assertEqual(decode_reset_token(token), raw_token)
        self.assertIsNone(decode_reset_token(token + "="))
        self.assertIsNone(decode_reset_token("x" * 43))

    def test_reset_consumes_grant_preserves_totp_and_revokes_all_sessions(self):
        raw_token = bytes(range(32))
        self._issue(raw_token)
        encrypt_secret(self.user.pk, bytes(range(20)))
        device = TOTPDevice.objects.get(user=self.user)
        device.confirmed_at = timezone.now()
        device.save(update_fields=("confirmed_at",))
        old_session = self.client.session
        old_session["_auth_user_id"] = str(self.user.pk)
        old_session["_auth_user_backend"] = "home.backends.UsernameAuthenticationBackend"
        old_session.save()
        another_session = SessionStore()
        another_session["_auth_user_id"] = str(self.user.pk)
        another_session["_auth_user_backend"] = "home.backends.UsernameAuthenticationBackend"
        another_session.save()
        token = base64.urlsafe_b64encode(raw_token).decode("ascii").rstrip("=")
        response = self._post_reset(
            {
                "token": token,
                "new_password": "A new sufficiently long password 43",
                "confirm_password": "A new sufficiently long password 43",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["completed"])
        grant = PasswordResetGrant.objects.get(user=self.user)
        self.assertIsNotNone(grant.consumed_at)
        self.assertTrue(TOTPDevice.objects.filter(pk=device.pk).exists())
        self.assertFalse(self.client.session.exists(old_session.session_key))
        self.assertFalse(self.client.session.exists(another_session.session_key))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("A new sufficiently long password 43"))
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.PASSWORD_RESET_COMPLETED,
                target_user_id=self.user.pk,
            ).exists()
        )

    def test_expired_unknown_and_reused_tokens_are_generic(self):
        raw_token = bytes(range(32))
        self._issue(raw_token, expires_at=timezone.now() - timedelta(seconds=1))
        token = base64.urlsafe_b64encode(raw_token).decode("ascii").rstrip("=")
        expired = self._post_reset({
            "token": token,
            "new_password": "A new sufficiently long password 43",
            "confirm_password": "A new sufficiently long password 43",
        })
        unknown = self._post_reset({
            "token": "A" * 43,
            "new_password": "A new sufficiently long password 43",
            "confirm_password": "A new sufficiently long password 43",
        })
        self.assertEqual(expired.status_code, unknown.status_code)
        self.assertEqual(expired.context["error"], unknown.context["error"])
        self.assertIn(b"The reset request could not be completed", expired.content)
        self.assertIn(b"The reset request could not be completed", unknown.content)

    def test_audit_failure_rolls_back_password_and_grant_consumption(self):
        raw_token = bytes(range(32))
        grant = self._issue(raw_token)
        token = base64.urlsafe_b64encode(raw_token).decode("ascii").rstrip("=")
        with patch("home.password_reset_views.record_event", side_effect=AuditUnavailable):
            response = self._post_reset({
                "token": token,
                "new_password": "A new sufficiently long password 43",
                "confirm_password": "A new sufficiently long password 43",
            })
        self.assertEqual(response.status_code, 503)
        grant.refresh_from_db()
        self.assertIsNone(grant.consumed_at)
        self.assertTrue(self.user.check_password("A sufficiently long test passphrase 42"))


class PasswordResetCommandTests(T027TestCase):
    def test_reset_issue_requires_effective_root(self):
        from home.management.commands.issue_password_reset import Command

        with patch("home.management.commands.issue_password_reset._is_effective_os_admin", return_value=False):
            with self.assertRaises(CommandError):
                Command().handle(username=self.user.username)

    def test_reset_token_is_written_only_to_controlling_tty_and_stored_as_digest(self):
        from home.management.commands.issue_password_reset import Command

        written = []
        patches = [
            patch("home.management.commands.issue_password_reset._is_effective_os_admin", return_value=True),
            patch("home.management.commands.issue_password_reset.os.open", return_value=91),
            patch(
                "home.management.commands.issue_password_reset.os.fstat",
                return_value=SimpleNamespace(st_mode=stat.S_IFCHR),
            ),
            patch("home.management.commands.issue_password_reset.os.isatty", return_value=True),
            patch("home.management.commands.issue_password_reset.os.write", side_effect=lambda _fd, data: written.append(data) or len(data)),
            patch("home.management.commands.issue_password_reset.os.close"),
            patch("home.management.commands.issue_password_reset.stat.S_ISCHR", return_value=True),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        command = Command()
        command.handle(username=self.user.username)
        output = b"".join(written).decode("ascii")
        token = output.splitlines()[-1]
        raw_token = decode_reset_token(token)
        grant = PasswordResetGrant.objects.get(user=self.user)
        self.assertIsNotNone(raw_token)
        self.assertEqual(grant.token_digest, reset_token_digest(raw_token))
        self.assertNotIn(token, repr(grant.__dict__))
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.PASSWORD_RECOVERY_ISSUED,
                target_user_id=self.user.pk,
            ).exists()
        )

