from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.db import close_old_connections, transaction
from django.test import TransactionTestCase

from home.models import ToolExecution
from home.tool_boundary import (AuthorizedToolExecutor, Ownership, SideEffect,
    ToolDeclaration, ToolDenied, ToolInvocation, ToolJournalUncertain, ToolRegistry, ToolRole)
from home.tool_journal import DatabaseToolJournal


class DurableToolJournalTests(TransactionTestCase):
    def setUp(self):
        self.calls = []
        self.audit = []
        self.journal = DatabaseToolJournal()
        self.declaration = ToolDeclaration(name='synthetic.write', required_role=ToolRole.USER,
            ownership=Ownership.ACTOR, side_effect=SideEffect.WRITE, confirmation_required=True,
            audit_event='tool.synthetic', schema={'type': 'object', 'properties': {'value': {'type': 'string'}}},
            handler=lambda args: self.calls.append(dict(args)))
        self.executor = AuthorizedToolExecutor(ToolRegistry((self.declaration,)),
            lambda invocation, outcome, declaration: self.audit.append(outcome.status), journal=self.journal)

    def invocation(self, operation_id=None):
        return ToolInvocation('synthetic.write', {'value': 'private synthetic input'}, 7, 7, ToolRole.USER,
                              confirmed=True, request_id=uuid4(), operation_id=operation_id or uuid4())

    def test_missing_journal_or_operation_id_denies_before_handler(self):
        without_journal = AuthorizedToolExecutor(ToolRegistry((self.declaration,)), lambda *_: None)
        with self.assertRaises(ToolDenied):
            without_journal.execute(self.invocation())
        invalid = ToolInvocation('synthetic.write', {'value': 'x'}, 7, 7, ToolRole.USER, confirmed=True)
        with self.assertRaises(ToolDenied):
            self.executor.execute(invalid)
        self.assertEqual(self.calls, [])
        self.assertFalse(ToolExecution.objects.exists())

    def test_completed_operation_cannot_be_replayed_and_stores_no_content(self):
        invocation = self.invocation()
        result = self.executor.execute(invocation)
        self.assertEqual((result.status, result.operation_id), ('succeeded', invocation.operation_id))
        row = ToolExecution.objects.get(operation_id=invocation.operation_id)
        self.assertEqual(row.state, 'succeeded')
        self.assertNotIn('private synthetic input', str(row.__dict__))
        with self.assertRaises(ValueError):
            row.delete()
        with self.assertRaises(ValueError):
            ToolExecution.objects.filter(pk=row.pk).delete()
        with self.assertRaises(ValueError):
            ToolExecution.objects.filter(pk=row.pk).update(state='started', finished_at=None)
        row.state = 'started'
        with self.assertRaises(ValueError):
            row.save()
        with self.assertRaises(ToolDenied):
            self.executor.execute(invocation)
        self.assertEqual(len(self.calls), 1)

    def test_outer_transaction_is_rejected_before_effect(self):
        with transaction.atomic():
            with self.assertRaises(ToolDenied):
                self.executor.execute(self.invocation())
        self.assertFalse(ToolExecution.objects.exists())
        self.assertEqual(self.calls, [])

    def test_unfinished_claim_and_failed_terminal_write_never_replay(self):
        invocation = self.invocation()
        with patch.object(self.journal, 'finish', side_effect=RuntimeError('synthetic')):
            with self.assertRaises(ToolJournalUncertain) as caught:
                self.executor.execute(invocation)
        self.assertEqual(caught.exception.operation_id, invocation.operation_id)
        self.assertEqual(ToolExecution.objects.get(pk=invocation.operation_id).state, 'started')
        with self.assertRaises(ToolDenied):
            self.executor.execute(invocation)
        self.assertEqual(len(self.calls), 1)

    def test_failed_start_audit_records_non_dispatch(self):
        invocation = self.invocation()
        def fail(*_args):
            raise RuntimeError('synthetic')
        executor = AuthorizedToolExecutor(ToolRegistry((self.declaration,)), fail, journal=self.journal)
        with self.assertRaises(ToolDenied):
            executor.execute(invocation)
        self.assertEqual(ToolExecution.objects.get(pk=invocation.operation_id).state, 'not_dispatched')
        self.assertEqual(self.calls, [])

    def test_failed_outcome_audit_preserves_unknown_state(self):
        from home.tool_boundary import ToolAuditUncertain
        invocation = self.invocation()
        def fail_after_start(_invocation, outcome, _declaration):
            if outcome.status != 'started':
                raise RuntimeError('synthetic')
        executor = AuthorizedToolExecutor(ToolRegistry((self.declaration,)), fail_after_start, journal=self.journal)
        with self.assertRaises(ToolAuditUncertain) as caught:
            executor.execute(invocation)
        self.assertEqual(caught.exception.operation_id, invocation.operation_id)
        self.assertEqual(ToolExecution.objects.get(pk=invocation.operation_id).state, 'unknown_effect')
        with self.assertRaises(ToolDenied):
            self.executor.execute(invocation)
        self.assertEqual(len(self.calls), 1)

    def test_two_connections_cannot_claim_same_operation(self):
        invocation = self.invocation()
        barrier = Barrier(2)
        def invoke(_):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                try:
                    return self.executor.execute(invocation).status
                except ToolDenied:
                    return 'denied'
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(invoke, range(2)))
        self.assertEqual(results.count('succeeded'), 1)
        self.assertEqual(results.count('denied'), 1)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(ToolExecution.objects.count(), 1)
