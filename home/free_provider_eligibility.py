"""Exact zero-total-cost eligibility for free-provider dispatch.

T179-B. Gate applied before any pre-dispatch request so that no request is
sent for a route that does not satisfy the exact zero-total-cost contract.

Eligibility is decomposed into four exact checks plus two gate checks:

* Account level   - the configured plan is the documented free plan and no
                    payment method or other billing mechanism is on record.
* Model level     - the model is on the approved zero-price catalog.
* Upstream level  - the upstream vendor id is exactly the approved id.
* Privacy/disclosure- the principal has accepted the model-specific
                    disclosure on this turn.
* Admin enablement- an administrator has explicitly enabled the free route.

Every check is exact and deterministic. Failure returns a reason string that is
rendered to the principal as the disclosure; it is never a silent fallback.
"""

from __future__ import annotations

import logging

from django.conf import settings

from home.openrouter_catalog import _zero_price
from home.openrouter_transport import is_approved_route

logger = logging.getLogger(__name__)

_free_plan = None
_billing_methods = None


class FreeRouteError(RuntimeError):
    """A free-route eligibility check failed."""


def _freeze() -> None:
    global _free_plan, _billing_methods
    _free_plan = getattr(settings, "SUPERHARRY_FREE_PLAN", "free")
    _billing_methods = getattr(settings, "SUPERHARRY_BILLING_METHODS", [])
    if not isinstance(_billing_methods, list):
        _billing_methods = list(_billing_methods)


def _billing_has_method() -> bool:
    _freeze()
    return any(str(method).strip() for method in _billing_methods)


def _approved_model_zero_cost(model_id: str) -> bool:
    """Require explicit application approval; public catalog metadata is discovery only."""
    _freeze()
    allowed = getattr(settings, 'SUPERHARRY_APPROVED_FREE_MODELS', None)
    return isinstance(allowed, (list, tuple, set, frozenset)) and model_id in allowed


def verify_free_route_eligibility(*, provider: str, model_id: str,
                                  upstream_id: str | None = None,
                                  risk_accepted: bool = False,
                                  admin_enabled: bool = False) -> str:
    """Return the empty string when the route is exactly zero-cost eligible.

    Returns a human-readable reason (the disclosure) on the first failed check.
    Yes is authoritative; a single failed check blocks dispatch and never falls
    back to a secondary route.
    """
    _freeze()
    if provider not in ("groq", "openrouter"):
        return "route_provider_invalid"

    if not admin_enabled:
        return "admin_free_route_not_enabled"

    if _free_plan != "free":
        return "account_not_free_plan"

    if _billing_has_method():
        return "account_has_payment_method"

    if not isinstance(model_id, str) or not model_id:
        return "model_id_invalid"

    if not _approved_model_zero_cost(model_id):
        return "model_not_approved_zero_cost"

    if provider == "openrouter":
        if not isinstance(upstream_id, str) or not upstream_id:
            return "upstream_id_invalid"
        if not is_approved_route(model_id, upstream_id):
            return "upstream_not_approved"

    if not isinstance(risk_accepted, bool) or not risk_accepted:
        return "disclosure_not_accepted"

    return ""


def free_route_enabled() -> bool:
    """Admin enablement: must be True before any free-provider dispatch."""
    return bool(getattr(settings, "SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED", False))
