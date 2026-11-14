#!/usr/bin/env python3
"""Read-only, loopback-only OmniRoute health and authentication probes.

This script does not make generation requests or establish provider admission,
accounting, release readiness, or upstream model eligibility. Set
OMNIROUTE_ENDPOINT and OMNIROUTE_API_KEY in the calling environment.
"""

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

import requests


@dataclass(frozen=True)
class ProbeResult:
    name: str
    passed: bool
    status: int | None


def _gateway_base(value: str) -> str:
    """Reject remote destinations, URL credentials and ambiguous paths."""
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError):
        raise ValueError("gateway_endpoint_invalid") from None
    if (parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1", "::1")
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or parsed.path not in ("", "/", "/v1", "/v1/")):
        raise ValueError("gateway_endpoint_invalid")
    # Avoid relying on host-file or DNS resolution for the loopback alias.
    host = "[::1]" if parsed.hostname == "::1" else "127.0.0.1"
    return f"http://{host}{':' + str(port) if port is not None else ''}"


def _gateway_key(value: str | None) -> str:
    if (not isinstance(value, str) or not value or not value.isascii()
            or any(not char.isprintable() or char.isspace() for char in value)):
        raise ValueError("gateway_credential_invalid")
    return value


class OmnirouteValidator:
    """Probe read-only endpoints without recording response bodies or keys."""

    def __init__(self, environ=None):
        environ = os.environ if environ is None else environ
        self.endpoint = _gateway_base(environ.get("OMNIROUTE_ENDPOINT", "http://127.0.0.1:20128"))
        self.api_key = _gateway_key(environ.get("OMNIROUTE_API_KEY"))
        self.results: list[ProbeResult] = []

    def run_all_tests(self) -> bool:
        self.results.clear()
        # Disabling environment proxies and redirects prevents a bearer key
        # from being forwarded to a different destination.
        with requests.Session() as session:
            session.trust_env = False
            probes = (
                ("health", "/api/health", {}, 200),
                ("models_unauthenticated", "/v1/models", {}, 401),
                ("models_authenticated", "/v1/models", {"Authorization": f"Bearer {self.api_key}"}, 200),
            )
            for name, path, headers, expected in probes:
                try:
                    response = session.get(self.endpoint + path, headers=headers, timeout=10,
                                           allow_redirects=False, stream=True)
                    try:
                        status = response.status_code
                    finally:
                        response.close()
                    self.results.append(ProbeResult(name, status == expected, status))
                except requests.RequestException:
                    # Exception text can contain headers, URLs or response data.
                    self.results.append(ProbeResult(name, False, None))
        return all(result.passed for result in self.results)

    def generate_report(self) -> str:
        lines = ["# OmniRoute read-only validation", "",
                 "This checks only local health and model endpoint authentication.",
                 "It does not validate generation, provider admission, or release acceptance.", ""]
        for result in self.results:
            outcome = "PASS" if result.passed else "FAIL"
            status = str(result.status) if result.status is not None else "request_failed"
            lines.append(f"- {result.name}: {outcome} ({status})")
        return "\n".join(lines) + "\n"


def main() -> int:
    try:
        validator = OmnirouteValidator()
        success = validator.run_all_tests()
        print(validator.generate_report(), end="")
        return 0 if success else 1
    except ValueError:
        print("Gateway configuration is invalid.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
