import re
from datetime import datetime, timedelta, timezone as datetime_timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

from django.contrib import admin as django_admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.contrib.sessions.models import Session
from django.db import OperationalError, transaction
from django.http import Http404, HttpResponse
from django.middleware.csrf import CSRF_SESSION_KEY
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import resolve, reverse
from django.utils import timezone

from home.authorization import (
    get_owned_conversation,
    get_owned_message,
    owned_conversations,
    owned_messages,
)
from home.audit import AuditUnavailable, record_event
from home.admin import AuditedUserAdmin
from home.middleware import SessionLifetimeMiddleware
from home.models import AuditEvent, AuditEventMutationError, Conversation, Message
from home.views import home


class ConversationStorageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="storage-user",
            password="test-password-123",
        )

    def test_conversation_has_uuid_owner_and_aware_access_timestamps(self):
        conversation = Conversation.objects.create(owner=self.user)

        self.assertEqual(conversation.owner, self.user)
        self.assertIsInstance(conversation.id, UUID)
        self.assertTrue(timezone.is_aware(conversation.created_at))
        self.assertTrue(timezone.is_aware(conversation.last_accessed_at))

    def test_messages_are_ordered_by_creation_time_then_primary_key(self):
        conversation = Conversation.objects.create(owner=self.user)
        created_at = timezone.now()
        first = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="First",
            created_at=created_at,
        )
        second = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content="Second",
            created_at=created_at,
        )

        self.assertEqual(list(conversation.messages.all()), [first, second])

    def test_deleting_conversation_cascades_to_messages(self):
        conversation = Conversation.objects.create(owner=self.user)
        message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Synthetic content",
        )

        conversation.delete()

        self.assertFalse(Message.objects.filter(pk=message.pk).exists())

    def test_deleting_user_cascades_to_conversations_and_messages(self):
        conversation = Conversation.objects.create(owner=self.user)
        message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content="Synthetic content",
        )

        self.user.delete()

        self.assertFalse(Conversation.objects.filter(pk=conversation.pk).exists())
        self.assertFalse(Message.objects.filter(pk=message.pk).exists())


class ConversationAuthorizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.owner = user_model.objects.create_user(
            username="conversation-owner",
            password="test-password-123",
        )
        cls.other_user = user_model.objects.create_user(
            username="conversation-other",
            password="test-password-123",
        )
        cls.staff_user = user_model.objects.create_user(
            username="conversation-staff",
            password="test-password-123",
            is_staff=True,
        )
        cls.superuser = user_model.objects.create_superuser(
            username="conversation-superuser",
            email="superuser@example.test",
            password="test-password-123",
        )
        cls.conversation = Conversation.objects.create(owner=cls.owner)
        cls.message = Message.objects.create(
            conversation=cls.conversation,
            role=Message.Role.USER,
            content="Private conversation content",
        )

    def test_owner_can_query_only_their_conversations_and_messages(self):
        self.assertEqual(list(owned_conversations(self.owner)), [self.conversation])
        self.assertEqual(
            get_owned_conversation(self.owner, self.conversation.pk),
            self.conversation,
        )
        self.assertEqual(
            list(owned_messages(self.owner, self.conversation.pk)),
            [self.message],
        )
        self.assertEqual(
            get_owned_message(
                self.owner,
                self.conversation.pk,
                self.message.pk,
            ),
            self.message,
        )

    def test_other_user_gets_404_for_conversation_and_message(self):
        self.assertFalse(owned_conversations(self.other_user).exists())
        self.assertFalse(
            owned_messages(self.other_user, self.conversation.pk).exists()
        )
        with self.assertRaises(Http404):
            get_owned_conversation(self.other_user, self.conversation.pk)
        with self.assertRaises(Http404):
            get_owned_message(
                self.other_user,
                self.conversation.pk,
                self.message.pk,
            )

    def test_anonymous_user_cannot_query_persistent_conversations_or_messages(self):
        anonymous_user = AnonymousUser()

        self.assertFalse(owned_conversations(anonymous_user).exists())
        self.assertFalse(
            owned_messages(anonymous_user, self.conversation.pk).exists()
        )
        with self.assertRaises(Http404):
            get_owned_conversation(anonymous_user, self.conversation.pk)
        with self.assertRaises(Http404):
            get_owned_message(
                anonymous_user,
                self.conversation.pk,
                self.message.pk,
            )

    def test_staff_and_superuser_roles_do_not_bypass_owner_scope(self):
        for privileged_user in (self.staff_user, self.superuser):
            with self.subTest(user=privileged_user.username):
                self.assertFalse(owned_conversations(privileged_user).exists())
                with self.assertRaises(Http404):
                    get_owned_conversation(privileged_user, self.conversation.pk)
                with self.assertRaises(Http404):
                    get_owned_message(
                        privileged_user,
                        self.conversation.pk,
                        self.message.pk,
                    )


class AuditEventTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="audit-user",
            password="test-password-123",
        )

    def test_writer_persists_only_the_approved_typed_fields(self):
        event = record_event(
            event_type=AuditEvent.EventType.LOGIN_SUCCEEDED,
            outcome=AuditEvent.Outcome.SUCCESS,
            actor_kind=AuditEvent.ActorKind.USER,
            actor_user_id=self.user.pk,
            target_user_id=self.user.pk,
        )

        self.assertEqual(event.event_type, AuditEvent.EventType.LOGIN_SUCCEEDED)
        self.assertEqual(event.actor_user_id, self.user.pk)
        self.assertEqual(event.target_user_id, self.user.pk)
        self.assertIsNotNone(event.event_id)
        self.assertTrue(timezone.is_aware(event.occurred_at))
        self.assertEqual(
            {field.name for field in AuditEvent._meta.fields},
            {
                "event_id",
                "occurred_at",
                "event_type",
                "outcome",
                "actor_kind",
                "actor_user_id",
                "target_user_id",
                "aggregate_count",
                "request_id",
            },
        )

    def test_unknown_account_failure_does_not_store_a_target_identity(self):
        event = record_event(
            event_type=AuditEvent.EventType.PASSWORD_VERIFICATION_FAILED,
            outcome=AuditEvent.Outcome.FAILURE,
            actor_kind=AuditEvent.ActorKind.SERVICE,
        )

        self.assertIsNone(event.actor_user_id)
        self.assertIsNone(event.target_user_id)

    def test_aggregate_signal_requires_a_positive_count_and_target(self):
        event = record_event(
            event_type=AuditEvent.EventType.SESSION_RESOLUTION_FAILURE_SIGNAL,
            outcome=AuditEvent.Outcome.SIGNAL,
            actor_kind=AuditEvent.ActorKind.SERVICE,
            target_user_id=self.user.pk,
            aggregate_count=5,
        )

        self.assertEqual(event.aggregate_count, 5)
        with self.assertRaises(ValueError):
            record_event(
                event_type=AuditEvent.EventType.SESSION_RESOLUTION_FAILURE_SIGNAL,
                outcome=AuditEvent.Outcome.SIGNAL,
                actor_kind=AuditEvent.ActorKind.SERVICE,
                target_user_id=self.user.pk,
                aggregate_count=0,
            )
        with self.assertRaises(ValueError):
            record_event(
                event_type=AuditEvent.EventType.SESSION_RESOLUTION_FAILURE_SIGNAL,
                outcome=AuditEvent.Outcome.SIGNAL,
                actor_kind=AuditEvent.ActorKind.SERVICE,
                aggregate_count=1,
            )

    def test_writer_rejects_mismatched_event_outcome_and_actor(self):
        with self.assertRaises(ValueError):
            record_event(
                event_type=AuditEvent.EventType.LOGIN_SUCCEEDED,
                outcome=AuditEvent.Outcome.FAILURE,
                actor_kind=AuditEvent.ActorKind.USER,
                actor_user_id=self.user.pk,
                target_user_id=self.user.pk,
            )
        with self.assertRaises(ValueError):
            record_event(
                event_type=AuditEvent.EventType.LOGIN_SUCCEEDED,
                outcome=AuditEvent.Outcome.SUCCESS,
                actor_kind=AuditEvent.ActorKind.SERVICE,
                target_user_id=self.user.pk,
            )
        with self.assertRaises(ValueError):
            record_event(
                event_type="auth.unapproved_event",
                outcome=AuditEvent.Outcome.SUCCESS,
                actor_kind=AuditEvent.ActorKind.USER,
                actor_user_id=self.user.pk,
            )

    def test_writer_maps_database_failures_to_audit_unavailable(self):
        with patch(
            "home.audit.AuditEvent.objects.create",
            side_effect=OperationalError("synthetic database failure"),
        ):
            with self.assertRaises(AuditUnavailable):
                record_event(
                    event_type=AuditEvent.EventType.LOGIN_SUCCEEDED,
                    outcome=AuditEvent.Outcome.SUCCESS,
                    actor_kind=AuditEvent.ActorKind.USER,
                    actor_user_id=self.user.pk,
                    target_user_id=self.user.pk,
                )

    def test_event_and_protected_change_can_roll_back_together(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                record_event(
                    event_type=AuditEvent.EventType.LOGIN_SUCCEEDED,
                    outcome=AuditEvent.Outcome.SUCCESS,
                    actor_kind=AuditEvent.ActorKind.USER,
                    actor_user_id=self.user.pk,
                    target_user_id=self.user.pk,
                )
                raise RuntimeError("synthetic protected-operation failure")

        self.assertFalse(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.LOGIN_SUCCEEDED,
                actor_user_id=self.user.pk,
            ).exists()
        )

    def test_user_id_snapshots_survive_account_deletion(self):
        user_id = self.user.pk
        record_event(
            event_type=AuditEvent.EventType.USER_DEACTIVATED,
            outcome=AuditEvent.Outcome.SUCCESS,
            actor_kind=AuditEvent.ActorKind.USER,
            actor_user_id=user_id,
            target_user_id=user_id,
        )

        self.user.delete()

        event = AuditEvent.objects.get(
            event_type=AuditEvent.EventType.USER_DEACTIVATED,
        )
        self.assertEqual(event.actor_user_id, user_id)
        self.assertEqual(event.target_user_id, user_id)

    def test_audit_events_are_append_only_through_model_and_queryset_apis(self):
        event = record_event(
            event_type=AuditEvent.EventType.LOGIN_SUCCEEDED,
            outcome=AuditEvent.Outcome.SUCCESS,
            actor_kind=AuditEvent.ActorKind.USER,
            actor_user_id=self.user.pk,
            target_user_id=self.user.pk,
        )

        event.outcome = AuditEvent.Outcome.FAILURE
        with self.assertRaises(AuditEventMutationError):
            event.save()
        with self.assertRaises(AuditEventMutationError):
            event.delete()
        with self.assertRaises(AuditEventMutationError):
            AuditEvent.objects.filter(pk=event.pk).update(
                outcome=AuditEvent.Outcome.FAILURE,
            )
        with self.assertRaises(AuditEventMutationError):
            AuditEvent.objects.filter(pk=event.pk).delete()

        event.refresh_from_db()
        self.assertEqual(event.outcome, AuditEvent.Outcome.SUCCESS)


@override_settings(SUPERHARRY_HOSTNAME="testserver")
class AuditedAuditAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = get_user_model().objects.create_superuser(
            username="audit-reader",
            email="audit-reader@example.test",
            password="test-password-123",
        )
        self.client.force_login(self.admin_user)

    def _get(self, url, data=None, **extra):
        return self.client.get(url, data, secure=True, **extra)

    def _create_export_event(self, *, occurred_at=None):
        return AuditEvent.objects.create(
            event_type=AuditEvent.EventType.ADMIN_AUDIT_EXPORTED,
            outcome=AuditEvent.Outcome.SUCCESS,
            actor_kind=AuditEvent.ActorKind.USER,
            actor_user_id=self.admin_user.pk,
            occurred_at=occurred_at or timezone.now() - timedelta(minutes=5),
        )

    def _grant_audit_permission(self, user):
        permission = Permission.objects.get(
            content_type__app_label="home",
            codename="view_auditevent",
        )
        user.user_permissions.add(permission)

    def test_anonymous_and_unauthorized_users_cannot_read_audit_events(self):
        self.client.logout()
        response = self._get(reverse("admin-audit-list"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("admin:login"))

        staff_user = get_user_model().objects.create_user(
            username="audit-staff",
            password="test-password-123",
            is_staff=True,
        )
        self.client.force_login(staff_user)
        for route in ("admin-audit-list", "admin-audit-export"):
            response = self._get(reverse(route))
            self.assertEqual(response.status_code, 403)
        self.assertNotContains(self._get(reverse("home")), reverse("admin-audit-list"))
        self.assertFalse(AuditEvent.objects.exists())

        non_staff = get_user_model().objects.create_user(
            username="audit-permitted-user",
            password="test-password-123",
        )
        self._grant_audit_permission(non_staff)
        self.client.force_login(non_staff)
        for route in ("admin-audit-list", "admin-audit-export"):
            response = self._get(reverse(route))
            self.assertEqual(response.status_code, 403)
        self.assertFalse(AuditEvent.objects.exists())

    def test_staff_user_with_permission_can_read_and_read_is_audited(self):
        user = get_user_model().objects.create_user(
            username="audit-permitted-staff",
            password="test-password-123",
            is_staff=True,
        )
        self._grant_audit_permission(user)
        self.client.force_login(user)

        response = self._get(reverse("admin-audit-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Audit events")
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.ADMIN_AUDIT_READ,
                actor_user_id=user.pk,
            ).exists()
        )
        self.assertContains(self._get(reverse("home")), reverse("admin-audit-list"))
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_audit_page_is_localized_in_spanish(self):
        response = self._get(
            reverse("admin-audit-list"),
            HTTP_ACCEPT_LANGUAGE="es",
        )

        self.assertContains(response, "Eventos de auditoría")

    def test_filters_use_utc_exclusive_end_and_reject_invalid_ranges(self):
        included = self._create_export_event(
            occurred_at=datetime(2026, 1, 1, 23, 59, tzinfo=datetime_timezone.utc),
        )
        self._create_export_event(
            occurred_at=datetime(2026, 1, 2, 0, 0, tzinfo=datetime_timezone.utc),
        )
        response = self._get(
            reverse("admin-audit-list"),
            {"start_date": "2026-01-01", "end_date": "2026-01-02"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([event.pk for event in response.context["events"]], [included.pk])
        self.assertEqual(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.ADMIN_AUDIT_READ,
                actor_user_id=self.admin_user.pk,
            ).count(),
            1,
        )

        invalid_response = self._get(
            reverse("admin-audit-list"),
            {"start_date": "2026-01-01", "end_date": "2026-02-02"},
        )
        self.assertEqual(invalid_response.status_code, 400)
        self.assertEqual(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.ADMIN_AUDIT_READ,
                actor_user_id=self.admin_user.pk,
            ).count(),
            1,
        )

    def test_signed_cursor_paginates_without_offsets_or_duplicates(self):
        timestamp = timezone.now() - timedelta(days=1)
        events = [
            self._create_export_event(occurred_at=timestamp)
            for _ in range(101)
        ]
        params = {
            "start_date": (timezone.localdate() - timedelta(days=2)).isoformat(),
            "end_date": timezone.localdate().isoformat(),
        }

        first_response = self._get(reverse("admin-audit-list"), params)
        self.assertEqual(first_response.status_code, 200)
        first_page = first_response.context["events"]
        self.assertEqual(len(first_page), 100)
        self.assertTrue(first_response.context["next_cursor"])

        params["cursor"] = first_response.context["next_cursor"]
        second_response = self._get(reverse("admin-audit-list"), params)
        self.assertEqual(second_response.status_code, 200)
        second_page = second_response.context["events"]
        self.assertEqual(len(second_page), 1)
        self.assertTrue(set(event.pk for event in first_page).isdisjoint(
            event.pk for event in second_page
        ))
        self.assertEqual(
            set(event.pk for event in first_page + second_page),
            {event.pk for event in events},
        )

        params["event_type"] = AuditEvent.EventType.ADMIN_AUDIT_EXPORTED
        mismatched_response = self._get(reverse("admin-audit-list"), params)
        self.assertEqual(mismatched_response.status_code, 400)

    def test_audit_read_failure_withholds_page_data(self):
        self._create_export_event()
        with patch("home.audit_views.record_event", side_effect=AuditUnavailable):
            response = self._get(reverse("admin-audit-list"))

        self.assertEqual(response.status_code, 503)
        self.assertNotIn(
            AuditEvent.EventType.ADMIN_AUDIT_EXPORTED.encode(),
            response.content,
        )

    def test_csv_export_is_bounded_and_audited_without_exposing_profile_data(self):
        self._create_export_event()

        response = self._get(reverse("admin-audit-export"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertLessEqual(len(response.content), 1024 * 1024)
        self.assertTrue(response.content.startswith(b"event_id,occurred_at,event_type"))
        self.assertNotIn(b"audit-reader", response.content)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.ADMIN_AUDIT_EXPORTED,
                actor_user_id=self.admin_user.pk,
            ).exists()
        )

    def test_csv_rejects_more_than_1000_rows_without_logging_export(self):
        AuditEvent.objects.bulk_create(
            [
                AuditEvent(
                    event_type=AuditEvent.EventType.ADMIN_AUDIT_EXPORTED,
                    outcome=AuditEvent.Outcome.SUCCESS,
                    actor_kind=AuditEvent.ActorKind.USER,
                    actor_user_id=self.admin_user.pk + 100000,
                )
                for _ in range(1001)
            ]
        )

        response = self._get(reverse("admin-audit-export"))

        self.assertEqual(response.status_code, 413)
        self.assertEqual(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.ADMIN_AUDIT_EXPORTED,
                actor_user_id=self.admin_user.pk + 100000,
                occurred_at__gte=timezone.now() - timedelta(hours=1),
            ).count(),
            1001,
        )

    def test_csv_rejects_encoded_output_over_one_mebibyte(self):
        with patch(
            "home.audit_views._csv_bytes",
            return_value=b"x" * (1024 * 1024 + 1),
        ):
            response = self._get(reverse("admin-audit-export"))

        self.assertEqual(response.status_code, 413)
        self.assertEqual(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.ADMIN_AUDIT_EXPORTED,
                actor_user_id=self.admin_user.pk,
            ).count(),
            0,
        )

    def test_csv_quota_is_per_admin_and_fails_closed_at_five_exports(self):
        for _ in range(5):
            self._create_export_event()

        response = self._get(reverse("admin-audit-export"))

        self.assertEqual(response.status_code, 429)
        self.assertEqual(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.ADMIN_AUDIT_EXPORTED,
                actor_user_id=self.admin_user.pk,
            ).count(),
            5,
        )

    def test_csv_quota_ignores_exports_older_than_one_hour(self):
        expired_at = timezone.now() - timedelta(hours=1, minutes=1)
        for _ in range(5):
            self._create_export_event(occurred_at=expired_at)

        response = self._get(reverse("admin-audit-export"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.ADMIN_AUDIT_EXPORTED,
                actor_user_id=self.admin_user.pk,
                occurred_at__gte=timezone.now() - timedelta(hours=1),
            ).count(),
            1,
        )

    def test_csv_audit_failure_withholds_export_data(self):
        self._create_export_event()
        exports_before = AuditEvent.objects.filter(
            event_type=AuditEvent.EventType.ADMIN_AUDIT_EXPORTED,
            actor_user_id=self.admin_user.pk,
        ).count()
        with patch("home.audit_views.record_event", side_effect=AuditUnavailable):
            response = self._get(reverse("admin-audit-export"))

        self.assertEqual(response.status_code, 503)
        self.assertNotIn(b"event_id,occurred_at,event_type", response.content)
        self.assertEqual(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.ADMIN_AUDIT_EXPORTED,
                actor_user_id=self.admin_user.pk,
            ).count(),
            exports_before,
        )


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    SUPERHARRY_HOSTNAME="testserver",
)
class AuditedUserAdminTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin_user = user_model.objects.create_superuser(
            username="audit-admin",
            email="audit-admin@example.test",
            password="test-password-123",
        )
        self.target_user = user_model.objects.create_user(
            username="audit-target",
            password="test-password-123",
        )
        self.user_admin = AuditedUserAdmin(user_model, django_admin.site)
        self.request = RequestFactory().post("/admin/auth/user/")
        self.request.user = self.admin_user

    def test_user_creation_is_audited(self):
        user_model = get_user_model()
        new_user = user_model(username="audit-created")

        self.user_admin.save_model(self.request, new_user, form=None, change=False)

        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.USER_CREATED,
                actor_user_id=self.admin_user.pk,
                target_user_id=new_user.pk,
            ).exists()
        )

    def test_admin_user_creation_and_audit_write_are_atomic(self):
        self.client.force_login(self.admin_user)
        url = reverse("admin:auth_user_add")
        response = self.client.post(
            url,
            {
                "username": "admin-created-user",
                "password1": "test-password-123",
                "password2": "test-password-123",
            },
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )

        self.assertEqual(response.status_code, 302, response.content.decode())
        created_user = get_user_model().objects.get(username="admin-created-user")
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.USER_CREATED,
                actor_user_id=self.admin_user.pk,
                target_user_id=created_user.pk,
            ).exists()
        )

        with patch("home.admin.record_event", side_effect=AuditUnavailable):
            failed_response = self.client.post(
                url,
                {
                    "username": "audit-failure-user",
                    "password1": "test-password-123",
                    "password2": "test-password-123",
                },
                secure=True,
                HTTP_ORIGIN="https://testserver",
            )

        self.assertEqual(failed_response.status_code, 503)
        self.assertFalse(
            get_user_model().objects.filter(username="audit-failure-user").exists()
        )

    def test_user_deactivation_and_role_changes_are_audited(self):
        self.target_user.is_active = False
        self.target_user.is_staff = True
        self.user_admin.save_model(
            self.request,
            self.target_user,
            form=None,
            change=True,
        )
        group = Group.objects.create(name="audit-role-change")
        form = SimpleNamespace(
            instance=self.target_user,
            save_m2m=lambda: self.target_user.groups.add(group),
        )
        self.user_admin.save_related(
            self.request,
            form,
            formsets=[],
            change=True,
        )

        event_types = set(
            AuditEvent.objects.filter(
                actor_user_id=self.admin_user.pk,
                target_user_id=self.target_user.pk,
            ).values_list("event_type", flat=True)
        )
        self.assertSetEqual(
            event_types,
            {
                AuditEvent.EventType.USER_DEACTIVATED,
                AuditEvent.EventType.ROLE_CHANGED,
            },
        )

    def test_hard_deletion_is_disabled_and_audit_model_is_not_registered(self):
        self.assertFalse(self.user_admin.has_delete_permission(self.request))
        self.assertFalse(django_admin.site.is_registered(AuditEvent))


class HomeRouteTests(TestCase):
    def test_root_route_is_registered_by_home_app(self):
        self.assertEqual(reverse("home"), "/")
        self.assertIs(resolve("/").func, home)


@override_settings(SUPERHARRY_HOSTNAME="testserver")
class AuthenticationPageTests(TestCase):
    def test_home_shows_login_link_to_anonymous_user(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Start a conversation")
        self.assertContains(response, reverse("login"))

    def test_home_uses_spanish_translation_catalog(self):
        response = self.client.get(reverse("home"), HTTP_ACCEPT_LANGUAGE="es")

        self.assertContains(response, "Iniciar una conversación")
        self.assertContains(response, "Iniciar sesión")

    def test_django_login_view_authenticates_user(self):
        user_model = get_user_model()
        user_model.objects.create_user(username="alice", password="test-password-123")

        response = self.client.post(
            reverse("login"),
            {"username": "alice", "password": "test-password-123"},
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )

        self.assertRedirects(response, reverse("home"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_authenticated_user_can_log_out_with_post(self):
        user_model = get_user_model()
        user_model.objects.create_user(username="alice", password="test-password-123")
        self.client.login(username="alice", password="test-password-123")

        response = self.client.post(
            reverse("logout"),
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )

        self.assertRedirects(response, reverse("home"))
        self.assertFalse(response.wsgi_request.user.is_authenticated)


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    SUPERHARRY_HOSTNAME="testserver",
)
class AuditedAuthenticationLifecycleTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="audit-lifecycle-user",
            password="test-password-123",
        )

    def test_successful_login_records_login_and_session_creation(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.user.username, "password": "test-password-123"},
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )

        self.assertRedirects(response, reverse("home"))
        self.assertSetEqual(
            set(
                AuditEvent.objects.filter(actor_user_id=self.user.pk).values_list(
                    "event_type",
                    flat=True,
                )
            ),
            {
                AuditEvent.EventType.LOGIN_SUCCEEDED,
                AuditEvent.EventType.SESSION_CREATED,
            },
        )

    def test_logout_records_event_within_the_session_transition(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("logout"),
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )

        self.assertRedirects(response, reverse("home"))
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.LOGOUT_SUCCEEDED,
                actor_user_id=self.user.pk,
                target_user_id=self.user.pk,
            ).exists()
        )

    def test_failed_password_audit_correlates_only_known_accounts(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.user.username, "password": "incorrect-password"},
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )
        self.assertEqual(response.status_code, 200)

        known_failure = AuditEvent.objects.get(
            event_type=AuditEvent.EventType.PASSWORD_VERIFICATION_FAILED,
        )
        self.assertEqual(known_failure.target_user_id, self.user.pk)
        self.assertIsNone(known_failure.actor_user_id)

        response = self.client.post(
            reverse("login"),
            {"username": "unknown-account", "password": "incorrect-password"},
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )
        self.assertEqual(response.status_code, 200)

        unknown_failure = AuditEvent.objects.latest("occurred_at")
        self.assertEqual(
            unknown_failure.event_type,
            AuditEvent.EventType.PASSWORD_VERIFICATION_FAILED,
        )
        self.assertIsNone(unknown_failure.target_user_id)

    def test_failed_login_fails_closed_when_audit_write_is_unavailable(self):
        with patch(
            "home.auth_views.record_event",
            side_effect=AuditUnavailable,
        ):
            response = self.client.post(
                reverse("login"),
                {"username": self.user.username, "password": "incorrect-password"},
                secure=True,
                HTTP_ORIGIN="https://testserver",
            )

        self.assertEqual(response.status_code, 503)
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type=AuditEvent.EventType.PASSWORD_VERIFICATION_FAILED,
            ).exists()
        )

    def test_login_fails_closed_when_required_audit_write_is_unavailable(self):
        with patch(
            "home.auth_views.record_event",
            side_effect=AuditUnavailable,
        ):
            response = self.client.post(
                reverse("login"),
                {"username": self.user.username, "password": "test-password-123"},
                secure=True,
                HTTP_ORIGIN="https://testserver",
            )

        self.assertEqual(response.status_code, 503)
        subsequent_response = self.client.get(reverse("home"))
        self.assertFalse(subsequent_response.wsgi_request.user.is_authenticated)

    def test_logout_fails_closed_when_required_audit_write_is_unavailable(self):
        self.client.force_login(self.user)

        with patch(
            "home.auth_views.record_event",
            side_effect=AuditUnavailable,
        ):
            response = self.client.post(
                reverse("logout"),
                secure=True,
                HTTP_ORIGIN="https://testserver",
            )

        self.assertEqual(response.status_code, 503)
        subsequent_response = self.client.get(reverse("home"))
        self.assertTrue(subsequent_response.wsgi_request.user.is_authenticated)


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    SUPERHARRY_HOSTNAME="testserver",
)
class DjangoSessionCsrfContractTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        get_user_model().objects.create_user(
            username="csrf-user",
            password="test-password-123",
        )

    def test_login_form_uses_session_backed_csrf_without_csrf_cookie(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertIn("__Host-superharry_session", self.client.cookies)
        self.assertNotIn("csrftoken", self.client.cookies)

    def test_legacy_csrf_token_endpoint_is_not_registered(self):
        response = self.client.get("/v1/session/csrf")

        self.assertEqual(response.status_code, 404)

    def test_admin_login_flushes_anonymous_session(self):
        get_user_model().objects.create_superuser(
            username="csrf-admin",
            password="test-password-123",
            email="admin@example.test",
        )
        response = self.client.get(reverse("admin:login"))
        match = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            response.content.decode(),
        )
        self.assertIsNotNone(match)
        anonymous_session_key = self.client.session.session_key

        response = self.client.post(
            reverse("admin:login"),
            {
                "username": "csrf-admin",
                "password": "test-password-123",
                "csrfmiddlewaretoken": match.group(1),
            },
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("admin:index"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertNotEqual(self.client.session.session_key, anonymous_session_key)
        self.assertFalse(
            Session.objects.filter(session_key=anonymous_session_key).exists()
        )

    def test_login_rejects_missing_csrf_token_without_authenticating(self):
        response = self.client.post(
            reverse("login"),
            {"username": "csrf-user", "password": "test-password-123"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_rejects_missing_csrf_token_without_ending_session(self):
        user = get_user_model().objects.get(username="csrf-user")
        self.client.force_login(user)

        response = self.client.post(
            reverse("logout"),
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_unsafe_request_rejects_missing_null_duplicate_and_malformed_origins(self):
        user = get_user_model().objects.get(username="csrf-user")
        self.client.force_login(user)
        response = self.client.get(reverse("home"), secure=True)
        match = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            response.content.decode(),
        )
        self.assertIsNotNone(match)
        token = match.group(1)

        invalid_origins = [
            None,
            "null",
            "https://testserver, https://testserver",
            "https://testserver/path",
            "https://testserver:invalid",
            "https://testserver:",
            "http://testserver",
            "https://attacker.example",
        ]
        for origin in invalid_origins:
            with self.subTest(origin=origin):
                headers = {"HTTP_ORIGIN": origin} if origin is not None else {}
                response = self.client.post(
                    reverse("logout"),
                    {"csrfmiddlewaretoken": token},
                    secure=True,
                    **headers,
                )
                self.assertEqual(response.status_code, 403)
                self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_unsafe_request_rejects_http_even_with_matching_http_origin(self):
        user = get_user_model().objects.get(username="csrf-user")
        self.client.force_login(user)
        response = self.client.post(
            reverse("logout"),
            HTTP_ORIGIN="http://testserver",
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_unsafe_request_accepts_valid_same_origin_https(self):
        user = get_user_model().objects.get(username="csrf-user")
        self.client.force_login(user)
        response = self.client.get(reverse("home"), secure=True)
        match = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            response.content.decode(),
        )
        self.assertIsNotNone(match)

        response = self.client.post(
            reverse("logout"),
            {"csrfmiddlewaretoken": match.group(1)},
            secure=True,
            HTTP_ORIGIN="https://testserver:443",
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    @override_settings(
        DEBUG=False,
        ALLOWED_HOSTS=["superharry.local"],
        SUPERHARRY_HOSTNAME="superharry.local",
    )
    def test_loopback_proxy_https_signal_allows_configured_local_origin(self):
        user = get_user_model().objects.get(username="csrf-user")
        self.client.force_login(user)
        response = self.client.get(
            reverse("home"),
            secure=True,
            HTTP_HOST="superharry.local",
        )
        match = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            response.content.decode(),
        )
        self.assertIsNotNone(match)

        response = self.client.post(
            reverse("logout"),
            {"csrfmiddlewaretoken": match.group(1)},
            HTTP_HOST="superharry.local",
            HTTP_ORIGIN="https://superharry.local",
            HTTP_X_FORWARDED_PROTO="https",
            REMOTE_ADDR="127.0.0.1",
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    @override_settings(
        DEBUG=False,
        ALLOWED_HOSTS=["superharry.local"],
        SUPERHARRY_HOSTNAME="superharry.local",
    )
    def test_non_loopback_cannot_spoof_trusted_proxy_https_signal(self):
        user = get_user_model().objects.get(username="csrf-user")
        self.client.force_login(user)
        response = self.client.get(
            reverse("home"),
            secure=True,
            HTTP_HOST="superharry.local",
        )
        match = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            response.content.decode(),
        )
        self.assertIsNotNone(match)

        response = self.client.post(
            reverse("logout"),
            {"csrfmiddlewaretoken": match.group(1)},
            HTTP_HOST="superharry.local",
            HTTP_ORIGIN="https://superharry.local",
            HTTP_X_FORWARDED_PROTO="https",
            REMOTE_ADDR="192.168.1.23",
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_flushes_anonymous_session_and_rotates_csrf_state(self):
        response = self.client.get(reverse("login"))
        match = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            response.content.decode(),
        )
        self.assertIsNotNone(match)
        anonymous_session_key = self.client.session.session_key
        anonymous_csrf_secret = self.client.session[CSRF_SESSION_KEY]
        self.client.session["anonymous_only"] = "discard this"
        self.client.session.save()

        response = self.client.post(
            reverse("login"),
            {
                "username": "csrf-user",
                "password": "test-password-123",
                "csrfmiddlewaretoken": match.group(1),
            },
            secure=True,
            HTTP_ORIGIN="https://testserver",
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertNotEqual(self.client.session.session_key, anonymous_session_key)
        self.assertFalse(
            Session.objects.filter(session_key=anonymous_session_key).exists()
        )
        self.assertNotIn("anonymous_only", self.client.session)
        self.assertNotEqual(
            self.client.session[CSRF_SESSION_KEY], anonymous_csrf_secret
        )

        session_cookie = response.cookies["__Host-superharry_session"]
        self.assertTrue(session_cookie["secure"])
        self.assertTrue(session_cookie["httponly"])
        self.assertEqual(session_cookie["samesite"], "Strict")
        self.assertEqual(session_cookie["path"], "/")
        self.assertEqual(session_cookie["domain"], "")
        self.assertNotIn("csrftoken", response.cookies)

    def test_login_rejects_cross_origin_even_with_valid_session_token(self):
        response = self.client.get(reverse("login"))
        match = re.search(
            r'name="csrfmiddlewaretoken" value="([^"]+)"',
            response.content.decode(),
        )
        self.assertIsNotNone(match)

        response = self.client.post(
            reverse("login"),
            {
                "username": "csrf-user",
                "password": "test-password-123",
                "csrfmiddlewaretoken": match.group(1),
            },
            secure=True,
            HTTP_ORIGIN="https://attacker.example",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_anonymous_session_has_fixed_ten_minute_lifetime(self):
        started_at = timezone.now().replace(microsecond=0)
        with patch("home.middleware.timezone.now", return_value=started_at):
            self.client.get(reverse("login"))
            original_session_key = self.client.session.session_key
            original_expiry = Session.objects.get(
                session_key=original_session_key
            ).expire_date

        self.assertEqual(original_expiry, started_at + timedelta(minutes=10))

        with patch(
            "home.middleware.timezone.now",
            return_value=started_at + timedelta(minutes=5),
        ):
            self.client.get(reverse("login"))

        self.assertEqual(
            Session.objects.get(session_key=original_session_key).expire_date,
            original_expiry,
        )

        with patch(
            "home.middleware.timezone.now",
            return_value=started_at + timedelta(minutes=10),
        ):
            self.client.get(reverse("login"))

        self.assertNotEqual(self.client.session.session_key, original_session_key)

    def test_authenticated_session_uses_idle_and_absolute_deadlines(self):
        started_at = timezone.now().replace(microsecond=0)
        with patch("home.middleware.timezone.now", return_value=started_at):
            response = self.client.get(reverse("login"))
            csrf_token = re.search(
                r'name="csrfmiddlewaretoken" value="([^"]+)"',
                response.content.decode(),
            ).group(1)
            self.client.post(
                reverse("login"),
                {
                    "username": "csrf-user",
                    "password": "test-password-123",
                    "csrfmiddlewaretoken": csrf_token,
                },
                secure=True,
                HTTP_ORIGIN="https://testserver",
            )
            authenticated_session_key = self.client.session.session_key
            initial_expiry = Session.objects.get(
                session_key=authenticated_session_key
            ).expire_date

        self.assertEqual(initial_expiry, started_at + timedelta(minutes=60))

        with patch(
            "home.middleware.timezone.now",
            return_value=started_at + timedelta(minutes=30),
        ):
            self.client.get(reverse("home"))

        self.assertEqual(
            Session.objects.get(session_key=authenticated_session_key).expire_date,
            initial_expiry,
        )

        with patch(
            "home.middleware.timezone.now",
            return_value=started_at + timedelta(minutes=61),
        ):
            response = self.client.get(reverse("home"))

        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_session_activity_never_extends_past_absolute_deadline(self):
        started_at = timezone.now().replace(microsecond=0)
        now = started_at + timedelta(hours=23, minutes=59)

        class InMemorySession(dict):
            def set_expiry(self, expiry):
                self.expiry = expiry

        request = SimpleNamespace(
            method="POST",
            user=SimpleNamespace(is_authenticated=True),
            session=InMemorySession(
                {
                    "_superharry_authenticated_started_at": int(
                        started_at.timestamp()
                    ),
                    "_superharry_authenticated_last_activity_at": int(
                        (now - timedelta(minutes=1)).timestamp()
                    ),
                }
            ),
        )

        with patch("home.middleware.timezone.now", return_value=now):
            SessionLifetimeMiddleware(lambda _: None).process_response(
                request,
                HttpResponse(status=302),
            )

        self.assertEqual(request.session.expiry, started_at + timedelta(hours=24))


class ChatShellTests(TestCase):
    def test_home_renders_accessible_chat_shell_and_responsive_asset(self):
        response = self.client.get(reverse("home"))

        self.assertContains(response, 'href="#main-content"')
        self.assertContains(response, 'aria-label="Primary navigation"')
        self.assertContains(response, 'id="main-content"')
        self.assertContains(response, '<label for="chat-message">Message</label>')
        self.assertContains(response, "disabled")
        self.assertContains(response, "home/chat.css")

        stylesheet = Path(__file__).parent / "static" / "home" / "chat.css"
        css = stylesheet.read_text(encoding="utf-8")
        self.assertIn("@media (max-width: 48rem)", css)
        self.assertIn(":focus-visible", css)

    def test_administration_navigation_requires_existing_staff_permission(self):
        user_model = get_user_model()
        regular_user = user_model.objects.create_user(username="regular", password="test-password-123")
        self.client.force_login(regular_user)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, reverse("admin:index"))

        staff_user = user_model.objects.create_user(
            username="staff",
            password="test-password-123",
            is_staff=True,
        )
        self.client.force_login(staff_user)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, reverse("admin:index"))

        view_users = Permission.objects.get(content_type__app_label="auth", codename="view_user")
        staff_user.user_permissions.add(view_users)
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("admin:index"))
