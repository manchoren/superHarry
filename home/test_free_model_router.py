import hashlib
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest import TestCase
from uuid import uuid4

from home.constitution_context import ConstitutionSnapshot, PreparedContext, _bundle_digest
from home.model_interface import (
    CapabilityEntry, CapabilityReport, CapabilityRequirements, CapabilityStatus,
    ContentPart, ContentTrust, ContextManifest, InvocationContext, MessageRole,
    ModelCapability, ModelCancelled, ModelCompleted, ModelError, ModelErrorCategory, ModelFailed,
    ModelMessage, ModelMode, ModelRequest, ModelStarted, ModelTextDelta,
    ModelToolCallProposal, OutcomeCertainty, RequestChannel, RequesterRole,
)
from home.free_model_router import Candidate, FreeModelRouter, RouterError


class FakeAdapter:
    def __init__(self, name, events):
        now = datetime.now(timezone.utc)
        self.capability_report = CapabilityReport(name, '1', 'synthetic', now - timedelta(seconds=1), now + timedelta(hours=1), (
            CapabilityEntry(ModelCapability.TEXT_GENERATION, CapabilityStatus.SUPPORTED),
        ))
        self.events = events
        self.calls = 0

    def stream(self, request, context):
        self.calls += 1
        yield from self.events


def failed(category, certainty, retryable=True):
    return ModelFailed(2, ModelError(category, 'synthetic_failure', retryable, certainty))


class FreeRouterTests(TestCase):
    def setUp(self):
        text = 'Complete synthetic constitution'
        raw = text.encode()
        prepared = PreparedContext(
            'superharry.context-bundle.v1', ConstitutionSnapshot('constitution.md', hashlib.sha256(raw).hexdigest(), len(raw), text),
            'hello', b'synthetic', 'test', '1', 'test', '1', 'test', '1', 10, 100, 5, 0, '',
        )
        prepared = replace(prepared, bundle_digest=_bundle_digest(prepared))
        self.id = uuid4()
        self.request = ModelRequest(self.id, (
            ModelMessage(MessageRole.DEVELOPER, (ContentPart(text, ContentTrust.PROTECTED, 'constitution.md'),)),
            ModelMessage(MessageRole.USER, (ContentPart('hello', ContentTrust.USER, 'user'),)),
        ), ContextManifest(prepared), CapabilityRequirements(frozenset({ModelCapability.TEXT_GENERATION})))
        self.context = InvocationContext(self.id, uuid4(), RequesterRole.USER, RequestChannel.WEB,
                                         ModelMode.AUTOMATIC, 'test', 'en', principal_id='1')
        self.clock = 10.0
        self.router = FreeModelRouter(clock=lambda: self.clock)
        self.allowed = lambda c, r, x: True
        self.eligible = lambda c, r, x: True
        self.current = lambda candidate, prepared: True

    def candidate(self, name, events):
        adapter = FakeAdapter(name, [ModelStarted(1, name, '1'), *events])
        return Candidate(name, adapter, 'group:' + name, 60), adapter

    def collect(self, candidates, request=None, context=None, allowed=None, current=None, eligibility=None):
        return list(self.router.stream(request or self.request, context or self.context, candidates,
                                      authorize=allowed or self.allowed, verify_eligibility=eligibility or self.eligible, verify_context=current or self.current))

    def test_quota_rejection_rotates_and_cooldown_expires(self):
        first, a = self.candidate('one', [failed(ModelErrorCategory.RATE_LIMIT, OutcomeCertainty.DEFINITIVE)])
        second, b = self.candidate('two', [ModelTextDelta(2, 'ok'), ModelCompleted(3)])
        events = self.collect((first, second))
        self.assertEqual([type(e) for e in events], [ModelStarted, ModelTextDelta, ModelCompleted])
        self.assertEqual(events[0].adapter_id, 'two')
        self.assertEqual((a.calls, b.calls), (1, 1))
        self.collect((first, second))
        self.assertEqual((a.calls, b.calls), (1, 2))
        self.clock = 71.0
        self.collect((first, second))
        self.assertEqual((a.calls, b.calls), (2, 3))

    def test_pre_dispatch_failure_can_rotate(self):
        first, a = self.candidate('one', [failed(ModelErrorCategory.UNAVAILABLE, OutcomeCertainty.NOT_DISPATCHED)])
        second, b = self.candidate('two', [ModelCompleted(2)])
        self.assertEqual(self.collect((first, second))[-1], ModelCompleted(2))
        self.assertEqual((a.calls, b.calls), (1, 1))

    def test_unknown_or_partial_result_never_rotates(self):
        for events in (
            [failed(ModelErrorCategory.TIMEOUT, OutcomeCertainty.UNKNOWN)],
            [ModelTextDelta(2, 'partial'), ModelFailed(3, ModelError(ModelErrorCategory.RATE_LIMIT, 'synthetic', True, OutcomeCertainty.DEFINITIVE))],
            [ModelToolCallProposal(2, 'id', 'tool', '{}', True), ModelFailed(3, ModelError(ModelErrorCategory.RATE_LIMIT, 'synthetic', True, OutcomeCertainty.DEFINITIVE))],
        ):
            with self.subTest(events=events):
                first, a = self.candidate('one', events)
                second, b = self.candidate('two', [ModelCompleted(2)])
                self.assertIsInstance(self.collect((first, second))[-1], ModelFailed)
                self.assertEqual((a.calls, b.calls), (1, 0))

    def test_guest_local_and_mismatched_request_block_before_calls(self):
        c, a = self.candidate('one', [ModelCompleted(2)])
        guest = replace(self.context, role=RequesterRole.GUEST, principal_id=None, guest_session_ref=uuid4())
        for context in (guest, replace(self.context, mode=ModelMode.LOCAL), replace(self.context, request_id=uuid4())):
            with self.subTest(context=context):
                with self.assertRaises(RouterError): self.collect((c,), context=context)
        self.assertEqual(a.calls, 0)

    def test_missing_authorization_or_stale_context_never_dispatches(self):
        c, a = self.candidate('one', [ModelCompleted(2)])
        with self.assertRaises(RouterError): self.collect((c,), allowed=lambda *args: False)
        def stale(_, __): raise RuntimeError('sensitive stale details')
        with self.assertRaises(RouterError) as raised: self.collect((c,), current=stale)
        self.assertNotIn('sensitive', str(raised.exception))
        self.assertEqual(a.calls, 0)

    def test_unexpected_exception_and_invalid_stream_do_not_rotate(self):
        class Broken(FakeAdapter):
            def stream(self, request, context):
                self.calls += 1
                raise RuntimeError('private details')
        adapter = Broken('one', [])
        first = Candidate('one', adapter, 'group:one', 1)
        second, b = self.candidate('two', [ModelCompleted(2)])
        with self.assertRaises(RouterError) as raised: self.collect((first, second))
        self.assertNotIn('private', str(raised.exception))
        self.assertEqual((adapter.calls, b.calls), (1, 0))

    def test_context_and_authorization_are_rechecked_per_provider(self):
        first, a = self.candidate('one', [failed(ModelErrorCategory.RATE_LIMIT, OutcomeCertainty.DEFINITIVE)])
        second, b = self.candidate('two', [ModelCompleted(2)])
        seen = []
        def verify(candidate, prepared):
            seen.append(candidate.provider_id)
            if candidate.provider_id == 'two':
                raise RuntimeError('stale')
            return True
        with self.assertRaises(RouterError): self.collect((first, second), current=verify)
        self.assertEqual((a.calls, b.calls), (1, 0))
        self.assertEqual(seen, ['one', 'one', 'one', 'two'])

    def test_excluded_candidate_is_never_called(self):
        first, a = self.candidate('one', [ModelCompleted(2)])
        second, b = self.candidate('two', [ModelCompleted(2)])
        result = self.collect((first, second), allowed=lambda candidate, *_: candidate.provider_id == 'two')
        self.assertEqual(result[0].adapter_id, 'two')
        self.assertEqual((a.calls, b.calls), (0, 1))

    def test_stream_is_closed_before_rotating(self):
        closed = []
        class Closing(FakeAdapter):
            def stream(self, request, context):
                self.calls += 1
                try:
                    yield ModelStarted(1, 'one', '1')
                    yield failed(ModelErrorCategory.RATE_LIMIT, OutcomeCertainty.DEFINITIVE)
                finally:
                    closed.append(True)
        adapter = Closing('one', [])
        second, b = self.candidate('two', [ModelCompleted(2)])
        result = self.collect((Candidate('one', adapter, 'group:one', 1), second))
        self.assertEqual(result[0].adapter_id, 'two')
        self.assertEqual(closed, [True])
        self.assertEqual(b.calls, 1)

    def test_context_false_or_none_blocks_before_dispatch(self):
        candidate, adapter = self.candidate('one', [ModelCompleted(2)])
        for result in (None, False):
            with self.subTest(result=result):
                with self.assertRaises(RouterError):
                    self.collect((candidate,), current=lambda *_: result)
        self.assertEqual(adapter.calls, 0)

    def test_context_becoming_stale_midstream_stops_without_failover(self):
        first, adapter = self.candidate('one', [ModelTextDelta(2, 'partial'), ModelCompleted(3)])
        second, backup = self.candidate('two', [ModelCompleted(2)])
        checks = []
        def verify(*_):
            checks.append(True)
            return len(checks) < 4
        events = self.router.stream(self.request, self.context, (first, second), authorize=self.allowed, verify_eligibility=self.eligible, verify_context=verify)
        self.assertIsInstance(next(events), ModelStarted)
        self.assertIsInstance(next(events), ModelTextDelta)
        with self.assertRaises(RouterError): next(events)
        self.assertEqual((adapter.calls, backup.calls), (1, 0))

    def test_close_failure_is_redacted_and_blocks_failover(self):
        class CloseFailure:
            def __init__(self):
                self.iterator = iter((ModelStarted(1, 'one', '1'), failed(ModelErrorCategory.RATE_LIMIT, OutcomeCertainty.DEFINITIVE)))
            def __iter__(self): return self
            def __next__(self): return next(self.iterator)
            def close(self): raise RuntimeError('private credential')
        class BrokenClose(FakeAdapter):
            def stream(self, request, context):
                self.calls += 1
                return CloseFailure()
        adapter = BrokenClose('one', [])
        second, backup = self.candidate('two', [ModelCompleted(2)])
        with self.assertRaises(RouterError) as raised:
            self.collect((Candidate('one', adapter, 'group:one', 1), second))
        self.assertNotIn('private credential', str(raised.exception))
        self.assertEqual((adapter.calls, backup.calls), (1, 0))

    def test_pre_cancelled_and_expired_requests_do_not_dispatch(self):
        class Signal:
            is_cancelled = True
        candidate, adapter = self.candidate('one', [ModelCompleted(2)])
        for context in (replace(self.context, cancellation=Signal()), replace(self.context, deadline=datetime.now(timezone.utc) - timedelta(seconds=1))):
            with self.subTest(context=context):
                with self.assertRaises(RouterError): self.collect((candidate,), context=context)
        self.assertEqual(adapter.calls, 0)

    def test_quota_group_shared_across_models_is_skipped_after_exhaustion(self):
        first, a = self.candidate('one', [failed(ModelErrorCategory.RATE_LIMIT, OutcomeCertainty.DEFINITIVE)])
        shared, b = self.candidate('two', [ModelCompleted(2)])
        independent, c = self.candidate('three', [ModelCompleted(2)])
        shared = replace(shared, quota_group=first.quota_group)
        result = self.collect((first, shared, independent))
        self.assertEqual(result[0].adapter_id, 'three')
        self.assertEqual((a.calls, b.calls, c.calls), (1, 0, 1))
        self.collect((shared, independent))
        self.assertEqual((b.calls, c.calls), (0, 2))
        self.clock = 71.0
        result = self.collect((shared, independent))
        self.assertEqual(result[0].adapter_id, 'two')
        self.assertEqual((b.calls, c.calls), (1, 2))

    def test_cancellation_after_dispatch_stops_without_failover(self):
        class Signal:
            is_cancelled = False
        signal = Signal()
        class Cancelling(FakeAdapter):
            def stream(self, request, context):
                self.calls += 1
                yield ModelStarted(1, 'one', '1')
                signal.is_cancelled = True
                yield ModelTextDelta(2, 'not displayed')
                yield ModelCompleted(3)
        adapter = Cancelling('one', [])
        second, backup = self.candidate('two', [ModelCompleted(2)])
        with self.assertRaises(RouterError):
            self.collect((Candidate('one', adapter, 'group:one', 1), second),
                         context=replace(self.context, cancellation=signal))
        self.assertEqual((adapter.calls, backup.calls), (1, 0))

    def test_paid_or_unverified_candidate_is_never_dispatched(self):
        first, paid = self.candidate('paid', [ModelCompleted(2)])
        second, free = self.candidate('free', [ModelCompleted(2)])
        events = self.collect((first, second), eligibility=lambda candidate, *_: candidate.provider_id == 'free')
        self.assertEqual(events[0].adapter_id, 'free')
        self.assertEqual((paid.calls, free.calls), (0, 1))
        for value in (False, None):
            with self.subTest(value=value):
                with self.assertRaises(RouterError):
                    self.collect((first,), eligibility=lambda *_: value)
        self.assertEqual(paid.calls, 0)

    def test_eligibility_exception_aborts_safely(self):
        first, adapter = self.candidate('one', [ModelCompleted(2)])
        def invalid(*_): raise RuntimeError('private details')
        with self.assertRaises(RouterError) as raised:
            self.collect((first,), eligibility=invalid)
        self.assertNotIn('private', str(raised.exception))
        self.assertEqual(adapter.calls, 0)

    def test_revocation_and_eligibility_change_before_dispatch_block_call(self):
        for changed in ('authorize', 'eligibility'):
            first, adapter = self.candidate('one', [ModelCompleted(2)])
            checks = []
            def revoked(*_):
                checks.append(True)
                return len(checks) == 1
            with self.subTest(changed=changed):
                kwargs = {'allowed': revoked} if changed == 'authorize' else {'eligibility': revoked}
                with self.assertRaises(RouterError): self.collect((first,), **kwargs)
                self.assertEqual(adapter.calls, 0)

    def test_adapter_cancellation_terminal_is_returned_without_failover(self):
        class Signal:
            is_cancelled = False
        signal = Signal()
        class Cancelling(FakeAdapter):
            def stream(self, request, context):
                self.calls += 1
                yield ModelStarted(1, 'one', '1')
                signal.is_cancelled = True
                yield ModelCancelled(2, backend_stop_confirmed=None)
        adapter = Cancelling('one', [])
        second, backup = self.candidate('two', [ModelCompleted(2)])
        result = self.collect((Candidate('one', adapter, 'group:one', 1), second),
                              context=replace(self.context, cancellation=signal))
        self.assertIsInstance(result[-1], ModelCancelled)
        self.assertEqual((adapter.calls, backup.calls), (1, 0))

    def test_revocation_during_stream_blocks_output_and_backup(self):
        first, adapter = self.candidate('one', [ModelTextDelta(2, 'private'), ModelCompleted(3)])
        second, backup = self.candidate('two', [ModelCompleted(2)])
        for changed in ('authorize', 'eligibility'):
            checks = []
            def revoked(*_):
                checks.append(True)
                return len(checks) < 3
            kwargs = {'allowed': revoked} if changed == 'authorize' else {'eligibility': revoked}
            with self.subTest(changed=changed):
                with self.assertRaises(RouterError): self.collect((first, second), **kwargs)
        self.assertEqual(adapter.calls, 2)
        self.assertEqual(backup.calls, 0)
