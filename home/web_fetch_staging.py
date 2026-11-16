"""Local-only destination policy for staged public web fetches.

This module deliberately performs no DNS or HTTP I/O.  Callers must provide
already-obtained DNS answers through ``resolve`` and validate every connection
and redirect before opening a socket.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence
from urllib.parse import urljoin, urlsplit


class FetchPolicyError(ValueError):
    """The URL or resolved destination cannot be used by a public fetch."""


Resolver = Callable[[str, int], Iterable[str]]


@dataclass(frozen=True)
class ValidatedDestination:
    url: str
    hostname: str
    port: int
    addresses: tuple[str, ...]


def _public_addresses(hostname: str, addresses: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in addresses:
        try:
            address = ipaddress.ip_address(str(value).strip())
        except ValueError as exc:
            raise FetchPolicyError("DNS returned an invalid address") from exc
        if not address.is_global:
            raise FetchPolicyError("destination is not public")
        text = str(address)
        if text not in normalized:
            normalized.append(text)
    if not normalized:
        raise FetchPolicyError("hostname has no DNS answers")
    return tuple(normalized)


def validate_destination(url: str, *, resolve: Resolver) -> ValidatedDestination:
    """Validate one URL and all of its DNS answers without performing I/O."""
    if (not isinstance(url, str) or not url or len(url) > 4096
            or any(character.isspace() for character in url)):
        raise FetchPolicyError("URL is invalid")
    try:
        parsed = urlsplit(url)
        hostname_value = parsed.hostname
    except ValueError as exc:
        raise FetchPolicyError("URL is invalid") from exc
    if parsed.scheme.lower() not in {"http", "https"}:
        raise FetchPolicyError("only HTTP(S) URLs are allowed")
    if parsed.username is not None or parsed.password is not None:
        raise FetchPolicyError("URL credentials are not allowed")
    if hostname_value is None or hostname_value != hostname_value.strip():
        raise FetchPolicyError("URL hostname is invalid")
    try:
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    except ValueError as exc:
        raise FetchPolicyError("URL port is invalid") from exc
    if not 1 <= port <= 65535:
        raise FetchPolicyError("URL port is invalid")
    hostname = hostname_value.rstrip(".").lower()
    if not hostname or any(character.isspace() for character in hostname):
        raise FetchPolicyError("URL hostname is invalid")
    try:
        addresses = resolve(hostname, port)
    except Exception as exc:
        raise FetchPolicyError("DNS resolution failed") from exc
    return ValidatedDestination(url=url, hostname=hostname, port=port,
                                addresses=_public_addresses(hostname, addresses))


def validate_redirect(
    current_url: str,
    location: str,
    *,
    resolve: Resolver,
    redirect_count: int,
    max_redirects: int = 5,
) -> ValidatedDestination:
    """Resolve and validate one redirect target, including its DNS answers."""
    if not isinstance(location, str) or not location or len(location) > 4096:
        raise FetchPolicyError("redirect location is invalid")
    if redirect_count >= max_redirects:
        raise FetchPolicyError("redirect limit exceeded")
    target = urljoin(current_url, location)
    return validate_destination(target, resolve=resolve)


def validate_redirect_chain(
    initial_url: str,
    locations: Sequence[str],
    *,
    resolve: Resolver,
    max_redirects: int = 5,
) -> tuple[ValidatedDestination, ...]:
    """Validate a synthetic redirect chain; this function never performs I/O."""
    if len(locations) > max_redirects:
        raise FetchPolicyError("redirect limit exceeded")
    current = validate_destination(initial_url, resolve=resolve)
    result = [current]
    for index, location in enumerate(locations):
        current = validate_redirect(current.url, location, resolve=resolve,
                                    redirect_count=index, max_redirects=max_redirects)
        result.append(current)
    return tuple(result)
