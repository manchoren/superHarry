from django.contrib.auth import get_user_model
from django.test import TestCase

from home.memory_access import authorize_memory_retrieval
from home.memory_agent_contract import (
    MAX_MEMORY_AGENT_ANSWER_CHARS,
    MAX_MEMORY_AGENT_REFERENCES,
    AuthorizedMemoryCandidates,
    MemoryAgentContractError,
    MemoryAgentResult,
    load_authorized_memory_candidates,
    validate_memory_agent_result,
)
from home.models import MemoryRecord


class MemoryAgentResultContractTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("memory-contract-owner", is_active=True)
        self.other = get_user_model().objects.create_user("memory-contract-other", is_active=True)
        self.record = MemoryRecord.objects.create(
            scope=MemoryRecord.Scope.USER, owner=self.user, content="authorized memory",
        )
        self.foreign_record = MemoryRecord.objects.create(
            scope=MemoryRecord.Scope.USER, owner=self.other, content="foreign memory",
        )
        self.authorization = authorize_memory_retrieval(
            self.user, route_authorized=True, reasoning_enabled=False,
        )
        self.candidates = load_authorized_memory_candidates(
            self.authorization, [self.record.pk],
        )

    def test_accepts_bounded_answer_and_authorized_references(self):
        result = validate_memory_agent_result(
            {"answer": "A bounded answer", "memory_ids": [self.record.pk]},
            candidates=self.candidates,
        )
        self.assertEqual(result, MemoryAgentResult("A bounded answer", (self.record.pk,)))

    def test_rejects_unauthorized_or_duplicate_reference(self):
        for value in (
            {"answer": "answer", "memory_ids": [self.foreign_record.pk]},
            {"answer": "answer", "memory_ids": [self.record.pk, self.record.pk]},
        ):
            with self.subTest(value=value), self.assertRaises(MemoryAgentContractError):
                validate_memory_agent_result(value, candidates=self.candidates)

    def test_candidate_loader_uses_database_authorization_and_principal_binding(self):
        with self.assertRaises(MemoryAgentContractError):
            load_authorized_memory_candidates(self.authorization, [self.foreign_record.pk])
        self.assertEqual(self.candidates.principal_id, self.user.pk)
        self.assertEqual(self.candidates.records[0].content, "authorized memory")

    def test_rejects_extra_fields_untrusted_principal_or_route_metadata(self):
        value = {"answer": "answer", "memory_ids": [], "user_id": 4, "route": "free"}
        with self.assertRaises(MemoryAgentContractError):
            validate_memory_agent_result(value, candidates=self.candidates)

    def test_rejects_malformed_answers_and_references(self):
        for value in (
            {"answer": " ", "memory_ids": []},
            {"answer": "x" * (MAX_MEMORY_AGENT_ANSWER_CHARS + 1), "memory_ids": []},
            {"answer": "answer", "memory_ids": ["not-a-uuid"]},
            {"answer": "answer", "memory_ids": [self.record.pk] * (MAX_MEMORY_AGENT_REFERENCES + 1)},
            {"answer": "invalid unicode \ud800", "memory_ids": []},
        ):
            with self.subTest(value=value), self.assertRaises(MemoryAgentContractError):
                validate_memory_agent_result(value, candidates=self.candidates)

    def test_rejects_forged_authorized_candidate_set(self):
        with self.assertRaises(MemoryAgentContractError):
            validate_memory_agent_result(
                {"answer": "answer", "memory_ids": []},
                candidates=[self.record.pk],
            )

    def test_candidate_constructor_is_not_public(self):
        with self.assertRaises(MemoryAgentContractError):
            AuthorizedMemoryCandidates(self.user.pk, ())
