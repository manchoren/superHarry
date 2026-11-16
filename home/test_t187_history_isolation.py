"""Existing history navigation must remain scoped to the owner."""

from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from home.audit import AuditUnavailable
from home.models import ApplicationBudgetReservation, AuditEvent, ChatEvent, ChatTurn, Conversation, GeminiChatJob, Message


@override_settings(DEBUG=True, ALLOWED_HOSTS=["testserver"], SUPERHARRY_HOSTNAME="testserver")
class HistoryIsolationTests(TestCase):
    def test_history_list_and_detail_do_not_expose_another_users_data(self):
        user = get_user_model().objects.create_user(username="history-owner")
        other = get_user_model().objects.create_user(username="history-other")
        old = timezone.now() - timedelta(days=1)
        own = Conversation.objects.create(owner=user, last_accessed_at=old)
        foreign = Conversation.objects.create(owner=other, last_accessed_at=old)
        Message.objects.create(conversation=own, role="user", content="own synthetic message")
        Message.objects.create(conversation=foreign, role="user", content="foreign synthetic message")
        self.client.force_login(user)

        response = self.client.get(reverse("conversation-detail", args=[own.pk]), secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "own synthetic message")
        self.assertNotContains(response, "foreign synthetic message")
        self.assertNotContains(response, str(foreign.pk))
        own.refresh_from_db()
        self.assertGreater(own.last_accessed_at, old)

        response = self.client.get(reverse("conversation-detail", args=[foreign.pk]), secure=True)
        self.assertEqual(response.status_code, 404)
        foreign.refresh_from_db()
        self.assertEqual(foreign.last_accessed_at, old)

    def test_confirmed_deletion_removes_owned_history_and_audits(self):
        user = get_user_model().objects.create_user(username='delete-owner')
        conversation = Conversation.objects.create(owner=user)
        message = Message.objects.create(conversation=conversation, role='user', content='synthetic')
        turn = ChatTurn.objects.create(conversation=conversation, user_message=message,
            idempotency_key=uuid4(), request_digest='0' * 64, model_mode='automatic', state='completed')
        event = ChatEvent.objects.create(turn=turn, sequence=1, event_type='turn.completed', payload={})
        job = GeminiChatJob.objects.create(turn=turn, state=GeminiChatJob.State.DONE)
        hold = ApplicationBudgetReservation.objects.create(
            operation_id=f'gateway:{turn.pk}:application-tokens', amount=10, state='unknown')
        self.client.force_login(user)
        url = reverse('conversation-delete', args=[conversation.pk])
        self.assertEqual(self.client.get(url, secure=True).status_code, 200)
        self.assertTrue(Conversation.objects.filter(pk=conversation.pk).exists())
        self.assertEqual(self.client.post(url, {}, secure=True, HTTP_ORIGIN='https://testserver').status_code, 400)
        response = self.client.post(url, {'confirm': 'delete'}, secure=True, HTTP_ORIGIN='https://testserver')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Conversation.objects.filter(pk=conversation.pk).exists())
        self.assertFalse(Message.objects.filter(pk=message.pk).exists())
        self.assertFalse(ChatTurn.objects.filter(pk=turn.pk).exists())
        self.assertFalse(ChatEvent.objects.filter(pk=event.pk).exists())
        self.assertFalse(GeminiChatJob.objects.filter(pk=job.pk).exists())
        hold.refresh_from_db()
        self.assertEqual(hold.state, 'unknown')
        self.assertTrue(AuditEvent.objects.filter(event_type=AuditEvent.EventType.CHAT_CONVERSATION_DELETED,
            actor_user_id=user.pk, target_user_id=user.pk).exists())

    def test_foreign_conversation_and_missing_csrf_are_denied(self):
        user = get_user_model().objects.create_user(username='delete-user')
        other = get_user_model().objects.create_user(username='delete-other')
        foreign = Conversation.objects.create(owner=other)
        own = Conversation.objects.create(owner=user)
        self.client.force_login(user)
        url = reverse('conversation-delete', args=[foreign.pk])
        self.assertEqual(self.client.get(url, secure=True).status_code, 404)
        self.assertEqual(self.client.post(url, {'confirm': 'delete'}, secure=True, HTTP_ORIGIN='https://testserver').status_code, 404)
        self.client.handler.enforce_csrf_checks = True
        self.assertEqual(self.client.post(reverse('conversation-delete', args=[own.pk]), {'confirm': 'delete'},
            secure=True, HTTP_ORIGIN='https://testserver').status_code, 403)
        self.assertEqual(Conversation.objects.filter(pk__in=[own.pk, foreign.pk]).count(), 2)

    def test_deactivated_owner_cannot_use_a_stale_session_for_history_or_deletion(self):
        user = get_user_model().objects.create_user(username='deactivated-history-owner')
        conversation = Conversation.objects.create(owner=user)
        Message.objects.create(conversation=conversation, role='user', content='private history')
        self.client.force_login(user)
        get_user_model().objects.filter(pk=user.pk).update(is_active=False)

        detail = self.client.get(reverse('conversation-detail', args=[conversation.pk]), secure=True)
        delete = self.client.get(reverse('conversation-delete', args=[conversation.pk]), secure=True)

        self.assertIn(detail.status_code, (302, 404))
        self.assertIn(delete.status_code, (302, 404))
        self.assertNotIn(b'private history', detail.content)
        self.assertTrue(Conversation.objects.filter(pk=conversation.pk).exists())
        self.assertFalse(AuditEvent.objects.filter(
            event_type=AuditEvent.EventType.CHAT_CONVERSATION_DELETED,
            target_user_id=user.pk,
        ).exists())

    def test_active_or_unresolved_work_blocks_deletion(self):
        user = get_user_model().objects.create_user(username='active-owner')
        conversation = Conversation.objects.create(owner=user)
        message = Message.objects.create(conversation=conversation, role='user', content='synthetic')
        turn = ChatTurn.objects.create(conversation=conversation, user_message=message,
            idempotency_key=uuid4(), request_digest='0' * 64, model_mode='automatic')
        job = GeminiChatJob.objects.create(turn=turn)
        self.client.force_login(user)
        url = reverse('conversation-delete', args=[conversation.pk])
        for state, job_state in [('queued', 'queued'), ('running', 'claimed'),
                                 ('cancel_requested', 'claimed'), ('failed', 'interrupted')]:
            with self.subTest(state=state, job_state=job_state):
                ChatTurn.objects.filter(pk=turn.pk).update(state=state)
                GeminiChatJob.objects.filter(pk=job.pk).update(state=job_state)
                response = self.client.post(url, {'confirm': 'delete'}, secure=True, HTTP_ORIGIN='https://testserver')
                self.assertEqual(response.status_code, 409)
                self.assertTrue(Conversation.objects.filter(pk=conversation.pk).exists())

    def test_returned_interrupted_worker_can_be_deleted_after_terminal_turn(self):
        user = get_user_model().objects.create_user(username='returned-worker-owner')
        conversation = Conversation.objects.create(owner=user)
        message = Message.objects.create(conversation=conversation, role='user', content='synthetic')
        turn = ChatTurn.objects.create(conversation=conversation, user_message=message,
            idempotency_key=uuid4(), request_digest='0' * 64, model_mode='automatic',
            state=ChatTurn.State.FAILED)
        job = GeminiChatJob.objects.create(turn=turn, state=GeminiChatJob.State.INTERRUPTED,
            worker_finished_at=timezone.now())
        self.client.force_login(user)

        response = self.client.post(reverse('conversation-delete', args=[conversation.pk]),
            {'confirm': 'delete'}, secure=True, HTTP_ORIGIN='https://testserver')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Conversation.objects.filter(pk=conversation.pk).exists())
        self.assertFalse(GeminiChatJob.objects.filter(pk=job.pk).exists())

    def test_audit_failure_rolls_back_deletion(self):
        user = get_user_model().objects.create_user(username='audit-delete-owner')
        conversation = Conversation.objects.create(owner=user)
        self.client.force_login(user)
        with patch('home.views.record_event', side_effect=AuditUnavailable):
            response = self.client.post(reverse('conversation-delete', args=[conversation.pk]),
                {'confirm': 'delete'}, secure=True, HTTP_ORIGIN='https://testserver')
        self.assertEqual(response.status_code, 503)
        self.assertTrue(Conversation.objects.filter(pk=conversation.pk).exists())
