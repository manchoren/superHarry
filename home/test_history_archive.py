import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import SimpleTestCase, TransactionTestCase

from .backup_archive import BackupArchiveError, create_data_archive
from .backup_boundary import BackupEntry, create_backup_plan
from .history_archive import (
    HistoryArchiveError,
    create_verified_pre_restore_snapshot,
    export_history_archive,
    replace_staged_history,
    restore_history_archive,
    sqlite_history_write_gate,
    stage_history_archive,
)
from .history_restore import export_history
from .models import ChatTurn, Conversation, Message


class HistoryArchiveStageTests(SimpleTestCase):
    def test_source_recovery_point_and_owner_selection_are_validated_before_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = b'{"format_version":"fixture"}'
            entry = BackupEntry("data/history/owners/17.json", "17", len(payload),
                                hashlib.sha256(payload).hexdigest(), "conversation_history")
            plan = create_backup_plan(application_release="test", schema_version="1",
                                      recovery_point_id="source-rp", entries=[entry])
            archive = root / "source.zip"
            digest = create_data_archive(plan.manifest, {entry.path: payload}, archive)
            with self.assertRaises(BackupArchiveError):
                stage_history_archive(
                    archive, root / "wrong-rp", expected_archive_sha256=digest,
                    selected_archive_recovery_point_id="different-source-rp",
                    reviewed_owner_ids=[17],
                )
            with self.assertRaises(BackupArchiveError):
                stage_history_archive(
                    archive, root / "wrong-owner", expected_archive_sha256=digest,
                    selected_archive_recovery_point_id="source-rp",
                    reviewed_owner_ids=[18],
                )


class HistoryArchivePipelineTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.owner = get_user_model().objects.create_user("archive-owner", is_active=True)

    def _conversation(self, content):
        conversation = Conversation.objects.create(owner=self.owner)
        message = Message.objects.create(
            conversation=conversation, role=Message.Role.USER, content=content,
        )
        return conversation, message

    def _paths(self, root):
        return {
            "source": root / "source.zip",
            "stage": root / "stage",
            "pre": root / "pre-restore.zip",
        }

    def test_gate_uses_django_sqlite_begin_immediate_and_rejects_nesting(self):
        statements = []
        connection.ensure_connection()
        connection.connection.set_trace_callback(statements.append)
        try:
            with sqlite_history_write_gate():
                self.assertTrue(connection.in_atomic_block)
                self.assertTrue(any(statement.upper() == "BEGIN IMMEDIATE" for statement in statements))
                with self.assertRaisesRegex(HistoryArchiveError, "cannot_be_nested"):
                    with sqlite_history_write_gate():
                        pass
            self.assertFalse(connection.in_atomic_block)
        finally:
            connection.connection.set_trace_callback(None)

    def _source_archive(self, root):
        old_conversation, old_message = self._conversation("restored-from-source")
        paths = self._paths(root)
        digest = export_history_archive(
            owner_ids=[self.owner.pk], recovery_point_id="archive-source-17",
            destination=paths["source"],
        )
        return paths, digest, old_conversation, old_message

    def test_end_to_end_replace_creates_distinct_verified_pre_restore_receipt_before_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths, digest, archived_conversation, _ = self._source_archive(root)
            Conversation.objects.filter(owner=self.owner).delete()
            self._conversation("current-state-to-replace")
            confirmation_observations = []

            result = restore_history_archive(
                archive_path=paths["source"], expected_archive_sha256=digest,
                selected_archive_recovery_point_id="archive-source-17",
                owner_ids=[self.owner.pk], staging_root=paths["stage"],
                pre_restore_archive_path=paths["pre"],
                pre_restore_recovery_point_id="rollback-fresh-18",
                confirm=lambda staged, receipt: confirmation_observations.append((
                    paths["pre"].is_file(), staged.selected_archive_recovery_point_id,
                    receipt.recovery_point_id, receipt.archive_sha256,
                )) or True,
            )

            self.assertEqual(len(confirmation_observations), 1)
            existed, source_id, rollback_id, receipt_digest = confirmation_observations[0]
            self.assertTrue(existed)
            self.assertEqual(source_id, "archive-source-17")
            self.assertEqual(rollback_id, "rollback-fresh-18")
            self.assertNotEqual(source_id, rollback_id)
            self.assertEqual(hashlib.sha256(paths["pre"].read_bytes()).hexdigest(), receipt_digest)
            restored = Conversation.objects.get(owner=self.owner)
            self.assertEqual(restored.pk, result.conversation_id_map[archived_conversation.pk])
            self.assertEqual(restored.messages.get().content, "restored-from-source")

    def test_corrupt_archive_refuses_before_snapshot_or_live_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths, digest, conversation, message = self._source_archive(root)
            paths["source"].write_bytes(paths["source"].read_bytes() + b"corrupt")
            before = list(Message.objects.values_list("pk", "content"))
            with self.assertRaisesRegex(Exception, "archive digest mismatch"):
                restore_history_archive(
                    archive_path=paths["source"], expected_archive_sha256=digest,
                    selected_archive_recovery_point_id="archive-source-17",
                    owner_ids=[self.owner.pk], staging_root=paths["stage"],
                    pre_restore_archive_path=paths["pre"],
                    pre_restore_recovery_point_id="rollback-fresh-18",
                    confirm=lambda *_: True,
                )
            self.assertFalse(paths["pre"].exists())
            self.assertEqual(list(Message.objects.values_list("pk", "content")), before)
            self.assertTrue(Conversation.objects.filter(pk=conversation.pk).exists())
            self.assertTrue(Message.objects.filter(pk=message.pk).exists())

    def test_missing_or_invalid_receipt_refuses_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths, digest, conversation, message = self._source_archive(root)
            staged = stage_history_archive(
                paths["source"], paths["stage"], expected_archive_sha256=digest,
                selected_archive_recovery_point_id="archive-source-17",
                reviewed_owner_ids=[self.owner.pk],
            )
            before = list(Message.objects.values_list("pk", "content"))
            with sqlite_history_write_gate() as gate:
                with self.assertRaisesRegex(HistoryArchiveError, "verified_pre_restore_snapshot_required"):
                    replace_staged_history(staged, pre_restore_snapshot=None, gate=gate, confirmed=True)
                receipt = create_verified_pre_restore_snapshot(
                    owner_ids=(self.owner.pk,), recovery_point_id="rollback-fresh-18",
                    archive_path=paths["pre"],
                    gate=gate,
                )
                paths["pre"].write_bytes(paths["pre"].read_bytes() + b"tamper")
                with self.assertRaisesRegex(HistoryArchiveError, "receipt_invalid"):
                    replace_staged_history(staged, pre_restore_snapshot=receipt, gate=gate, confirmed=True)
            self.assertEqual(list(Message.objects.values_list("pk", "content")), before)
            self.assertTrue(Conversation.objects.filter(pk=conversation.pk).exists())
            self.assertTrue(Message.objects.filter(pk=message.pk).exists())

    def test_chat_turn_conflict_and_bulk_insert_interruption_preserve_current_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths, digest, _, _ = self._source_archive(root)
            Conversation.objects.filter(owner=self.owner).delete()
            current, current_message = self._conversation("must-survive-failure")
            turn = ChatTurn.objects.create(
                conversation=current, user_message=current_message,
                idempotency_key=uuid4(), request_digest="e" * 64,
                model_mode=ChatTurn.ModelMode.AUTOMATIC,
                state=ChatTurn.State.COMPLETED,
            )
            with self.assertRaisesRegex(Exception, "history_restore_chat_turn_conflict"):
                restore_history_archive(
                    archive_path=paths["source"], expected_archive_sha256=digest,
                    selected_archive_recovery_point_id="archive-source-17",
                    owner_ids=[self.owner.pk], staging_root=root / "stage-chat",
                    pre_restore_archive_path=root / "pre-chat.zip",
                    pre_restore_recovery_point_id="rollback-chat-18", confirm=lambda *_: True,
                )
            self.assertTrue(ChatTurn.objects.filter(pk=turn.pk).exists())
            self.assertEqual(Message.objects.get(pk=current_message.pk).content, "must-survive-failure")

            ChatTurn.objects.filter(pk=turn.pk).delete()
            before_conversations = list(Conversation.objects.values_list("pk", "owner_id"))
            before_messages = list(Message.objects.values_list("pk", "conversation_id", "content"))
            with patch.object(Message.objects, "bulk_create", side_effect=RuntimeError("synthetic interruption")):
                with self.assertRaisesRegex(RuntimeError, "synthetic interruption"):
                    restore_history_archive(
                        archive_path=paths["source"], expected_archive_sha256=digest,
                        selected_archive_recovery_point_id="archive-source-17",
                        owner_ids=[self.owner.pk], staging_root=root / "stage-rollback",
                        pre_restore_archive_path=root / "pre-rollback.zip",
                        pre_restore_recovery_point_id="rollback-rollback-18", confirm=lambda *_: True,
                    )
            self.assertEqual(list(Conversation.objects.values_list("pk", "owner_id")), before_conversations)
            self.assertEqual(list(Message.objects.values_list("pk", "conversation_id", "content")), before_messages)
