"""Fail-closed authorization primitives for T234 protected settings.

This module deliberately does not store or change personality or directives.
It only validates the authorization envelope for a future administrative UI.
"""

from dataclasses import dataclass


class PersonalityControlDenied(ValueError):
    """Raised when a protected personality/directive operation is unsafe."""


@dataclass(frozen=True)
class FixedDirectiveChangeAuthorization:
    actor_user_id: int
    proposed_directives: tuple[str, ...]


def authorize_fixed_directive_change(
    *, actor, current_directives, proposed_directives, confirmed
) -> FixedDirectiveChangeAuthorization:
    """Validate the administrative envelope without applying a change.

    The directive tuple is treated as an immutable protected baseline here:
    this helper cannot authorize edits to it, only prove that a future UI has
    an active administrator and an explicit confirmation for an unchanged
    baseline.  Runtime agents and unsaved/inactive users are rejected.
    """
    if actor is None or not getattr(actor, "is_authenticated", False):
        raise PersonalityControlDenied("An authenticated administrator is required.")
    if not getattr(actor, "is_active", False) or getattr(actor, "pk", None) is None:
        raise PersonalityControlDenied("The administrator account is unavailable.")
    if not (getattr(actor, "is_staff", False) or getattr(actor, "is_superuser", False)):
        raise PersonalityControlDenied("Administrator permission is required.")
    if confirmed is not True:
        raise PersonalityControlDenied("Explicit confirmation is required.")

    if isinstance(current_directives, (str, bytes)) or isinstance(
        proposed_directives, (str, bytes)
    ):
        raise PersonalityControlDenied("Directive values must be a sequence.")
    try:
        current = tuple(current_directives)
        proposed = tuple(proposed_directives)
    except (TypeError, ValueError) as exc:
        raise PersonalityControlDenied("Directive values must be a sequence.") from exc
    if not current or any(not isinstance(item, str) or not item.strip() for item in current):
        raise PersonalityControlDenied("The protected directive baseline is invalid.")
    if proposed != current:
        raise PersonalityControlDenied("Protected directives cannot be changed by this boundary.")
    return FixedDirectiveChangeAuthorization(actor_user_id=actor.pk, proposed_directives=current)
