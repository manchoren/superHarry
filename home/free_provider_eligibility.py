"""Configuration checks for free-provider dispatch.

T179-B. Gate applied before any pre-dispatch request so that no request is
sent for a route that does not satisfy the exact zero-total-cost contract.

Eligibility is decomposed into configuration checks plus two gate checks:

* Account level   - the configured plan is the documented free plan and no
                    payment method or other billing mechanism is on record.
* Model level     - the model is on the approved zero-price catalog.
* Upstream level  - the upstream vendor id is exactly the approved id.
* Privacy/disclosure- the principal has accepted the model-specific
                    disclosure on this turn.
* Admin enablement- an administrator has explicitly enabled the free route.

These settings are administrative declarations, not independent proof of an
account's billing state, upstream routing, privacy terms, or total cost. The
separate tokenizer and gateway gates remain closed without verified evidence.
"""

from __future__ import annotations

import logging

from django.conf import settings

from home.openrouter_catalog import _zero_price
from home.openrouter_transport import is_approved_route

logger = logging.getLogger(__name__)

class FreeRouteError(RuntimeError):
    """A free-route eligibility check failed."""


def _approved_model_zero_cost(model_id: str) -> bool:
    """Require explicit application approval; public catalog metadata is discovery only."""
    allowed = getattr(settings, 'SUPERHARRY_APPROVED_FREE_MODELS', None)
    return isinstance(allowed, (list, tuple, set, frozenset)) and model_id in allowed


def verify_free_route_eligibility(*, provider: str, model_id: str,
                                  upstream_id: str | None = None,
                                  risk_accepted: bool = False,
                                  admin_enabled: bool = False) -> str:
    """Return the empty string when configured eligibility checks pass.

    Returns a human-readable reason (the disclosure) on the first failed check.
    A successful result does not prove the account or upstream configuration.
    """
    if provider not in ("groq", "openrouter"):
        return "route_provider_invalid"

    if admin_enabled is not True:
        return "admin_free_route_not_enabled"

    if getattr(settings, "SUPERHARRY_FREE_PLAN", None) != "free":
        return "account_not_free_plan"

    billing = getattr(settings, "SUPERHARRY_BILLING_METHODS", None)
    if not isinstance(billing, (list, tuple)) or any(
        not isinstance(method, str) or not method.strip() for method in billing
    ):
        return "account_billing_unknown"
    if billing:
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
    return getattr(settings, "SUPERHARRY_FREE_ROUTE_ADMIN_ENABLED", False) is True
