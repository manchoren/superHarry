import hashlib
import json
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase

from home.history_restore import (
    HistoryRestoreError,
    MAX_REVIEWED_OWNERS,
    export_history,
    restore_history,
)
from home.models import ChatTurn, Conversation, Message


class HistoryRestoreTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user("history-owner", is_active=True)
        self.other = user_model.objects.create_user("history-other", is_active=True)

    def _conversation(self, owner, *, content="old", conversation_id=None):
        conversation = Conversation.objects.create(
            id=conversation_id or uuid4(), owner=owner,
        )
        message = Message.objects.create(
            conversation=conversation, role=Message.Role.USER, content=content,
        )
        return conversation, message

    def _archive(self, owners):
        return export_history(owner_ids=[owner.pk for owner in owners])

    def test_owner_scoped_replace_uses_new_message_ids_and_preserves_other_owner(self):
        source_conversation, source_message = self._conversation(self.owner, content="archived")
        other_conversation, other_message = self._conversation(self.other, content="untouched")
        payload, digest = self._archive([self.owner])
        self.assertEqual(set(json.loads(payload)), {
            "format_version", "owner_ids", "conversations", "messages",
        })

        Conversation.objects.filter(owner=self.owner).delete()
        current, current_message = self._conversation(self.owner, content="replace-me")
        result = restore_history(
            payload, expected_sha256=digest,
            reviewed_owner_ids=[self.owner.pk], confirmed=True,
        )

        self.assertEqual(result.conversations_replaced, 1)
        self.assertEqual(result.conversations_restored, 1)
        self.assertEqual(result.messages_restored, 1)
        restored_id = result.conversation_id_map[source_conversation.pk]
        restored = Conversation.objects.get(pk=restored_id)
        self.assertEqual(restored.owner_id, self.owner.pk)
        restored_message = restored.messages.get()
        self.assertEqual(restored_message.content, "archived")
        self.assertNotEqual(restored_message.pk, source_message.pk)
        self.assertEqual(result.message_id_map[source_message.pk], restored_message.pk)
        self.assertFalse(Conversation.objects.filter(pk=current.pk).exists())
        self.assertFalse(Message.objects.filter(pk=current_message.pk).exists())
        self.assertEqual(Conversation.objects.get(pk=other_conversation.pk).owner_id, self.other.pk)
        self.assertEqual(Message.objects.get(pk=other_message.pk).content, "untouched")

    def test_archived_conversation_id_collision_is_remapped_without_overwriting_other_owner(self):
        self._conversation(self.owner, content="archived-owner-history")
        payload, _ = self._archive([self.owner])
        document = json.loads(payload)
        foreign_conversation, foreign_message = self._conversation(
            self.other, content="other-owner-history",
        )
        old_archive_id = document["conversations"][0]["id"]
        document["conversations"][0]["id"] = str(foreign_conversation.pk)
        for row in document["messages"]:
            if row["conversation_id"] == old_archive_id:
                row["conversation_id"] = str(foreign_conversation.pk)
        collision_payload = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()

        result = restore_history(
            collision_payload,
            expected_sha256=hashlib.sha256(collision_payload).hexdigest(),
            reviewed_owner_ids=[self.owner.pk], confirmed=True,
        )

        mapped_id = result.conversation_id_map[foreign_conversation.pk]
        self.assertNotEqual(mapped_id, foreign_conversation.pk)
        self.assertEqual(Conversation.objects.get(pk=foreign_conversation.pk).owner_id, self.other.pk)
        self.assertEqual(Message.objects.get(pk=foreign_message.pk).content, "other-owner-history")
        self.assertEqual(Conversation.objects.get(pk=mapped_id).owner_id, self.owner.pk)
        self.assertEqual(Conversation.objects.get(pk=mapped_id).messages.get().content, "archived-owner-history")

    def test_conversation_id_collision_with_unselected_owner_is_remapped(self):
        source, _ = self._conversation(self.owner, content="archive")
        payload, _digest = self._archive([self.owner])
        document = json.loads(payload)

        # Give the archive a conversation UUID already owned by another user.
        collision, collision_message = self._conversation(self.other, content="preserve")
        old_id = document["conversations"][0]["id"]
        document["conversations"][0]["id"] = str(collision.pk)
        for row in document["messages"]:
            if row["conversation_id"] == old_id:
                row["conversation_id"] = str(collision.pk)
        rewritten = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(rewritten).hexdigest()

        result = restore_history(
            rewritten, expected_sha256=digest,
            reviewed_owner_ids=[self.owner.pk], confirmed=True,
        )
        mapped = result.conversation_id_map[collision.pk]
        self.assertNotEqual(mapped, collision.pk)
        self.assertEqual(Conversation.objects.get(pk=collision.pk).owner_id, self.other.pk)
        self.assertEqual(Message.objects.get(pk=collision_message.pk).content, "preserve")
        self.assertEqual(Conversation.objects.get(pk=mapped).owner_id, self.owner.pk)
        self.assertNotEqual(mapped, source.pk)

    def test_chat_turn_reference_blocks_before_any_mutation(self):
        conversation, message = self._conversation(self.owner, content="preserve-on-refusal")
        turn = ChatTurn.objects.create(
            conversation=conversation,
            user_message=message,
            idempotency_key=uuid4(),
            request_digest="a" * 64,
            model_mode=ChatTurn.ModelMode.AUTOMATIC,
            state=ChatTurn.State.COMPLETED,
        )
        payload, digest = self._archive([self.owner])
        before_conversations = list(Conversation.objects.values_list("id", "owner_id"))
        before_messages = list(Message.objects.values_list("id", "conversation_id", "content"))

        with self.assertRaisesRegex(HistoryRestoreError, "chat_turn_conflict"):
            restore_history(
                payload, expected_sha256=digest,
                reviewed_owner_ids=[self.owner.pk], confirmed=True,
            )

        self.assertEqual(list(Conversation.objects.values_list("id", "owner_id")), before_conversations)
        self.assertEqual(list(Message.objects.values_list("id", "conversation_id", "content")), before_messages)
        self.assertTrue(ChatTurn.objects.filter(pk=turn.pk).exists())

    def test_chat_turn_message_foreign_keys_block_even_when_turn_conversation_is_other_owner(self):
        target, target_user_message = self._conversation(self.owner, content="protected-user-message")
        target_assistant = Message.objects.create(
            conversation=target, role=Message.Role.ASSISTANT, content="protected-assistant-message",
        )
        foreign_conversation, foreign_user_message = self._conversation(
            self.other, content="foreign-turn-user-message",
        )
        second_foreign_conversation, second_foreign_message = self._conversation(
            self.other, content="second-foreign-turn-user-message",
        )
        user_ref_turn = ChatTurn.objects.create(
            conversation=foreign_conversation,
            user_message=target_user_message,
            idempotency_key=uuid4(),
            request_digest="b" * 64,
            model_mode=ChatTurn.ModelMode.AUTOMATIC,
            state=ChatTurn.State.COMPLETED,
        )
        assistant_ref_turn = ChatTurn.objects.create(
            conversation=second_foreign_conversation,
            user_message=second_foreign_message,
            assistant_message=target_assistant,
            idempotency_key=uuid4(),
            request_digest="c" * 64,
            model_mode=ChatTurn.ModelMode.AUTOMATIC,
            state=ChatTurn.State.COMPLETED,
        )
        payload, digest = self._archive([self.owner])
        before = list(Message.objects.values_list("id", "conversation_id", "content"))

        with self.assertRaisesRegex(HistoryRestoreError, "chat_turn_conflict"):
            restore_history(
                payload, expected_sha256=digest,
                reviewed_owner_ids=[self.owner.pk], confirmed=True,
            )

        self.assertEqual(list(Message.objects.values_list("id", "conversation_id", "content")), before)
        self.assertTrue(ChatTurn.objects.filter(pk=user_ref_turn.pk).exists())
        self.assertTrue(ChatTurn.objects.filter(pk=assistant_ref_turn.pk).exists())

    def test_injected_mid_transaction_failure_rolls_back_delete_and_inserts(self):
        old_conversation, old_message = self._conversation(self.owner, content="must-survive")
        payload, digest = self._archive([self.owner])
        original_bulk_create = Message.objects.bulk_create

        def fail_after_conversation_insert(objects, *args, **kwargs):
            raise RuntimeError("synthetic restore interruption")

        with patch.object(Message.objects, "bulk_create", side_effect=fail_after_conversation_insert):
            with self.assertRaisesRegex(RuntimeError, "synthetic restore interruption"):
                restore_history(
                    payload, expected_sha256=digest,
                    reviewed_owner_ids=[self.owner.pk], confirmed=True,
                )

        self.assertEqual(list(Conversation.objects.filter(owner=self.owner).values_list("id", flat=True)), [old_conversation.pk])
        self.assertEqual(list(Message.objects.filter(conversation=old_conversation).values_list("id", "content")), [(old_message.pk, "must-survive")])
        self.assertEqual(original_bulk_create.__self__, Message.objects)

    def test_unknown_owner_digest_mismatch_and_unconfirmed_restore_refuse(self):
        self._conversation(self.owner)
        payload, digest = self._archive([self.owner])
        original_ids = list(Conversation.objects.values_list("id", flat=True))
        cases = (
            ("digest", {"expected_sha256": "0" * 64, "reviewed_owner_ids": [self.owner.pk], "confirmed": True}),
            ("unconfirmed", {"expected_sha256": digest, "reviewed_owner_ids": [self.owner.pk], "confirmed": False}),
            ("unknown_owner", {"expected_sha256": digest, "reviewed_owner_ids": [self.owner.pk + 99999], "confirmed": True}),
        )
        for label, kwargs in cases:
            with self.subTest(label=label), self.assertRaises(HistoryRestoreError):
                restore_history(payload, **kwargs)
            self.assertEqual(list(Conversation.objects.values_list("id", flat=True)), original_ids)

    def test_payload_schema_rejects_extra_fields_duplicate_ids_and_bad_relation(self):
        self._conversation(self.owner)
        payload, _ = self._archive([self.owner])
        document = json.loads(payload)
        mutations = []
        extra = json.loads(payload)
        extra["users"] = [{"password": "must-never-import"}]
        mutations.append(extra)
        duplicate = json.loads(payload)
        duplicate["conversations"].append(dict(duplicate["conversations"][0]))
        mutations.append(duplicate)
        broken_relation = json.loads(payload)
        broken_relation["messages"][0]["conversation_id"] = str(uuid4())
        mutations.append(broken_relation)
        before = list(Conversation.objects.values_list("id", flat=True))
        for invalid in mutations:
            raw = json.dumps(invalid, sort_keys=True, separators=(",", ":")).encode()
            with self.subTest(invalid=invalid), self.assertRaises(HistoryRestoreError):
                restore_history(
                    raw, expected_sha256=hashlib.sha256(raw).hexdigest(),
                    reviewed_owner_ids=[self.owner.pk], confirmed=True,
                )
            self.assertEqual(list(Conversation.objects.values_list("id", flat=True)), before)

    def test_owner_review_list_is_bounded_before_database_access(self):
        too_many = list(range(1, MAX_REVIEWED_OWNERS + 2))
        with self.assertRaisesRegex(HistoryRestoreError, "owner_review_invalid"):
            export_history(owner_ids=too_many)
        with self.assertRaisesRegex(HistoryRestoreError, "owner_review_invalid"):
            restore_history(
                b"{}", expected_sha256=hashlib.sha256(b"{}").hexdigest(),
                reviewed_owner_ids=too_many, confirmed=True,
            )
