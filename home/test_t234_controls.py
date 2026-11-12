"""Focused validation coverage for the bounded T234 memory-control slice."""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import MemoryRecord
from django.contrib.auth import get_user_model


class T234MemoryControlValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="t234-owner")

    def test_confirmation_metadata_is_atomic(self):
        record = MemoryRecord(
            scope=MemoryRecord.Scope.USER,
            owner=self.user,
            content="bounded synthetic memory",
            confirmed_at=timezone.now(),
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Confirmation metadata must be provided together.",
        ):
            record.full_clean()

    def test_deleted_memory_requires_a_deletion_request(self):
        record = MemoryRecord(
            scope=MemoryRecord.Scope.USER,
            owner=self.user,
            content="bounded synthetic memory",
            deleted_at=timezone.now(),
        )

        with self.assertRaises(ValidationError):
            record.validate_constraints()

    def test_requested_deletion_can_be_recorded_before_final_deletion(self):
        record = MemoryRecord.objects.create(
            scope=MemoryRecord.Scope.USER,
            owner=self.user,
            content="bounded synthetic memory",
            retain_until=timezone.now() + timedelta(days=1),
            deletion_requested_at=timezone.now(),
        )

        self.assertIsNone(record.deleted_at)
        self.assertIsNotNone(record.deletion_requested_at)
