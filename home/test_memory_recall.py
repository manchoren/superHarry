from unittest import TestCase

from home.memory_recall import (
    MAX_RECALL_QUERY_CHARS,
    MemoryRecallDenied,
    RecallBudget,
    recall_memory,
)
from home.memory_access import MemoryRetrievalAuthorization


class MemoryRecallBoundaryTests(TestCase):
    authorization = MemoryRetrievalAuthorization(user_id=1)
    def result(self, **extra):
        value = {"status": "ok", "records": [], "summary": "none"}
        value.update(extra)
        return value

    def test_allows_bounded_main_agent_recall_and_audits_without_content(self):
        calls = []
        audit = []
        budget = RecallBudget(max_calls=2)
        result = recall_memory("what matters", "new context", budget=budget,
                               caller="main_agent", authorization=self.authorization,
                               invoke=lambda q, r, auth: (calls.append((q, r, auth)) or self.result()),
                               audit=lambda status, count, tokens: audit.append((status, count, tokens)))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(calls), 1)
        self.assertEqual((audit[0][0], audit[0][1]), ("succeeded", 1))

    def test_denies_guest_memory_agent_and_recursion_before_callback(self):
        calls = []
        for caller in ("guest", "memory_agent"):
            with self.subTest(caller=caller), self.assertRaises(MemoryRecallDenied):
                recall_memory("query", "reason", budget=RecallBudget(), caller=caller,
                              authorization=self.authorization, invoke=lambda *_: calls.append(1))
        budget = RecallBudget()
        def recursive(query, reason, authorization):
            return recall_memory(query, reason, budget=budget, caller="main_agent",
                                 authorization=authorization, invoke=recursive)
        with self.assertRaises(MemoryRecallDenied):
            recall_memory("query", "reason", budget=budget, caller="main_agent",
                          authorization=self.authorization, invoke=recursive)
        self.assertEqual(calls, [])

    def test_requires_server_created_retrieval_authorization(self):
        with self.assertRaises(MemoryRecallDenied):
            recall_memory("query", "reason", budget=RecallBudget(),
                          caller="main_agent", authorization=object(),
                          invoke=lambda *_: self.result())

    def test_hard_call_and_result_budget_is_fail_closed(self):
        calls = []
        budget = RecallBudget(max_calls=1)
        invoke = lambda *_: (calls.append(1) or self.result())
        recall_memory("one", "reason", budget=budget, caller="main_agent",
                      authorization=self.authorization, invoke=invoke)
        with self.assertRaises(MemoryRecallDenied):
            recall_memory("two", "reason", budget=budget, caller="main_agent",
                          authorization=self.authorization, invoke=invoke)
        self.assertEqual(len(calls), 1)

    def test_rejects_unbounded_inputs_and_malformed_results(self):
        cases = (("", "reason"), ("query", ""), ("x" * (MAX_RECALL_QUERY_CHARS + 1), "reason"))
        for query, reason in cases:
            with self.subTest(query=query[:8]), self.assertRaises(MemoryRecallDenied):
                recall_memory(query, reason, budget=RecallBudget(), caller="main_agent",
                              authorization=self.authorization, invoke=lambda *_: self.result())
        with self.assertRaises(MemoryRecallDenied):
            recall_memory("query", "reason", budget=RecallBudget(), caller="main_agent",
                          authorization=self.authorization, invoke=lambda *_: {"records": []})

    def test_audits_denials_and_callback_failures_without_memory_content(self):
        events = []
        with self.assertRaises(MemoryRecallDenied):
            recall_memory("query", "reason", budget=RecallBudget(), caller="guest",
                          authorization=self.authorization, invoke=lambda *_: self.result(),
                          audit=lambda status, count, tokens: events.append((status, count, tokens)))
        self.assertEqual(events, [("denied", 0, 0)])

        events.clear()
        def failing(*_):
            raise RuntimeError("provider detail must not escape")
        with self.assertRaises(MemoryRecallDenied):
            recall_memory("query", "reason", budget=RecallBudget(), caller="main_agent",
                          authorization=self.authorization, invoke=failing,
                          audit=lambda status, count, tokens: events.append((status, count, tokens)))
        self.assertEqual(events, [("failed", 1, 0)])

        events.clear()
        with self.assertRaises(MemoryRecallDenied):
            recall_memory("query", "reason", budget=RecallBudget(), caller="main_agent",
                          authorization=self.authorization, invoke=lambda *_: {"records": []},
                          audit=lambda status, count, tokens: events.append((status, count, tokens)))
        self.assertEqual(events[0][0], "failed")

    def test_error_result_is_not_audited_as_success(self):
        events = []
        result = recall_memory(
            "query", "reason", budget=RecallBudget(), caller="main_agent",
            authorization=self.authorization, invoke=lambda *_: {"status": "error"},
            audit=lambda status, count, tokens: events.append((status, count, tokens)),
        )
        self.assertEqual(result["status"], "error")
        self.assertEqual(events[0][0:2], ("failed", 1))
