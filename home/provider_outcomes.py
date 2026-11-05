"""Outcome classes shared by free-provider dispatch and routing."""


class NotDispatched(RuntimeError):
    """No generation request was sent; failover to the next provider is safe."""


class RateLimited(RuntimeError):
    """The provider rejected the request with a definitive HTTP 429; failover is safe."""


class OutcomeUnknown(RuntimeError):
    """A request may have been processed; never fail over or repeat."""
