from django.contrib.auth import get_user_model
from django.test import TestCase

from home.memory_access import authorize_memory_retrieval
from home.memory_retrieval import (
    MAX_CONTEXT_BYTES, MAX_RESULTS, MemoryRetrievalUnavailable,
    retrieve_authorized_memory_records, retrieve_memory_records,
)
from home.models import MemoryRecord


class MemoryRetrievalFallbackTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("owner", is_active=True)
        self.other = get_user_model().objects.create_user("other", is_active=True)
        self.match = MemoryRecord.objects.create(
            scope=MemoryRecord.Scope.USER, owner=self.user,
            content="La reunión será mañana en Quito",
        )
        self.foreign = MemoryRecord.objects.create(
            scope=MemoryRecord.Scope.USER, owner=self.other,
            content="La reunión será mañana en Quito",
        )
        MemoryRecord.objects.create(
            scope=MemoryRecord.Scope.GLOBAL, content="Recovery result is unknown",
        )

    def test_keyword_fallback_is_case_and_accent_insensitive_and_scoped(self):
        records, mode = retrieve_memory_records(user=self.user, query="REUNION", semantic_search=None)
        self.assertEqual(mode, "keyword")
        self.assertEqual([record.pk for record in records], [self.match.pk])

    def test_semantic_empty_or_error_falls_back_without_foreign_records(self):
        for adapter in (lambda *_: [], lambda *_: (_ for _ in ()).throw(RuntimeError("offline"))):
            records, mode = retrieve_memory_records(user=self.user, query="mañana", semantic_search=adapter)
            self.assertEqual(mode, "keyword")
            self.assertEqual([record.pk for record in records], [self.match.pk])

    def test_semantic_results_are_validated_against_authorized_scope(self):
        records, mode = retrieve_memory_records(
            user=self.user, query="mañana",
            semantic_search=lambda records, query, limit: [self.foreign],
        )
        self.assertEqual(mode, "keyword")
        self.assertEqual([record.pk for record in records], [self.match.pk])

    def test_semantic_lookalike_with_authorized_pk_is_rejected(self):
        lookalike = MemoryRecord(
            pk=self.match.pk,
            scope=MemoryRecord.Scope.USER,
            owner=self.user,
            content="unauthorized replacement",
        )
        records, mode = retrieve_memory_records(
            user=self.user, query="reunion",
            semantic_search=lambda records, query, limit: [lookalike],
        )
        self.assertEqual(mode, "keyword")
        self.assertEqual([record.pk for record in records], [self.match.pk])

    def test_query_and_limit_are_bounded(self):
        with self.assertRaises(MemoryRetrievalUnavailable):
            retrieve_memory_records(user=self.user, query=" ")
        with self.assertRaises(MemoryRetrievalUnavailable):
            retrieve_memory_records(user=self.user, query="x", limit=0)

    def test_authorized_path_bounds_context_charges_and_records_access(self):
        authorization = authorize_memory_retrieval(
            self.user, route_authorized=True, reasoning_enabled=False,
        )
        charged = []
        records, mode, usage = retrieve_authorized_memory_records(
            authorization=authorization, query="reunion", charge_usage=lambda value: charged.append(value) or True,
        )
        self.assertEqual(mode, "keyword")
        self.assertEqual([record.pk for record in records], [self.match.pk])
        self.assertEqual(charged, [usage])
        self.match.refresh_from_db()
        self.assertEqual(self.match.access_count, 1)
        self.assertLessEqual(usage, MAX_CONTEXT_BYTES)

    def test_authorized_path_requires_charge_and_rejects_foreign_output(self):
        authorization = authorize_memory_retrieval(
            self.user, route_authorized=True, reasoning_enabled=False,
        )
        with self.assertRaises(MemoryRetrievalUnavailable):
            retrieve_authorized_memory_records(
                authorization=authorization, query="reunion", charge_usage=None,
            )
        with self.assertRaises(MemoryRetrievalUnavailable):
            retrieve_authorized_memory_records(
                authorization=authorization, query="reunion",
                semantic_search=lambda records, query, limit: [self.foreign],
                charge_usage=lambda value: False,
            )
        with self.assertRaises(MemoryRetrievalUnavailable):
            retrieve_memory_records(user=self.user, query="x", limit=MAX_RESULTS + 1)
        with self.assertRaises(MemoryRetrievalUnavailable):
            retrieve_memory_records(user=self.user, query="x", limit=True)
