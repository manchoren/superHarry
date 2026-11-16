from django.contrib.auth import get_user_model
from django.test import TestCase

from .personality_controls import (
    PersonalityControlDenied,
    authorize_fixed_directive_change,
)


class FixedDirectiveAuthorizationTests(TestCase):
    def setUp(self):
        self.directives = ("protect safety", "respect authorized instructions")
        self.admin = get_user_model().objects.create_superuser(
            username="t234-admin", password="synthetic-password"
        )

    def test_active_admin_with_confirmation_can_prepare_unchanged_baseline(self):
        authorization = authorize_fixed_directive_change(
            actor=self.admin,
            current_directives=self.directives,
            proposed_directives=self.directives,
            confirmed=True,
        )
        self.assertEqual(authorization.actor_user_id, self.admin.pk)
        self.assertEqual(authorization.proposed_directives, self.directives)

    def test_non_admin_and_missing_confirmation_fail_closed(self):
        user = get_user_model().objects.create_user(
            username="t234-user", password="synthetic-password"
        )
        for actor, confirmed in ((user, True), (self.admin, False)):
            with self.subTest(actor=actor, confirmed=confirmed), self.assertRaises(
                PersonalityControlDenied
            ):
                authorize_fixed_directive_change(
                    actor=actor,
                    current_directives=self.directives,
                    proposed_directives=self.directives,
                    confirmed=confirmed,
                )

    def test_runtime_or_malformed_directive_change_is_rejected(self):
        cases = (
            (("protect safety", "changed"), "changed baseline"),
            ((), "empty baseline"),
            (("protect safety", ""), "blank directive"),
        )
        for proposed, label in cases:
            with self.subTest(label=label), self.assertRaises(PersonalityControlDenied):
                authorize_fixed_directive_change(
                    actor=self.admin,
                    current_directives=self.directives,
                    proposed_directives=proposed,
                    confirmed=True,
                )

    def test_scalar_directive_values_fail_closed(self):
        for current, proposed in (("protect safety", self.directives), (self.directives, "protect safety")):
            with self.subTest(current=current, proposed=proposed), self.assertRaises(
                PersonalityControlDenied
            ):
                authorize_fixed_directive_change(
                    actor=self.admin,
                    current_directives=current,
                    proposed_directives=proposed,
                    confirmed=True,
                )
