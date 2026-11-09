"""Read untrusted public model metadata without admitting or dispatching routes."""

import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


# Owner-approved model IDs, 2026-11-09. Discovery does not approve new IDs.
APPROVED_MODELS = frozenset((
    'liquid/lfm-3-1.7b:free',
    'recursive/flint-v1.0:free',
    'xingchen-agi/xing4.0-29b-a4b:free',
    'nvidia/nemotron-3.5-super-vl:free',
    'dots-studio/dots-3-note-preview:free',
    'liquid/lfm-2.5-2.6b:free',
    'nvidia/nemotron-3.5-lightning:free',
    'cohere/north-mini-code:free',
    'nvidia/nemotron-3-ultra-550b-a55b:free',
    'nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free',
    'google/gemma-4-26b-a4b-it:free',
    'google/gemma-4-31b-it:free',
))


_MAX_RESPONSE_BYTES = 4 * 1024 * 1024
_MAX_MODELS = 10000
_MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*:free\Z")
_FETCH_PROGRAM = '''import http.client, sys
connection = http.client.HTTPSConnection("openrouter.ai", timeout=5)
try:
    connection.request("GET", "/api/v1/models", headers={"Accept": "application/json"})
    response = connection.getresponse()
    if response.status != 200:
        sys.exit(1)
    sys.stdout.buffer.write(response.read(4194305))
finally:
    connection.close()
'''


class CatalogError(ValueError):
    """Public model metadata could not be read safely."""


@dataclass(frozen=True)
class CatalogModel:
    model_id: str
    context_length: int


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CatalogError("catalog_invalid")
        result[key] = value
    return result


def _zero_price(value):
    if not isinstance(value, str) or len(value) > 64:
        return False
    try:
        price = Decimal(value)
        return price.is_finite() and price == 0
    except InvalidOperation:
        return False


def parse_catalog(raw):
    """Select text models with zero listed prices, never implying total cost."""
    if not isinstance(raw, bytes) or len(raw) > _MAX_RESPONSE_BYTES:
        raise CatalogError("catalog_invalid")
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                              parse_constant=lambda _: (_ for _ in ()).throw(CatalogError("catalog_invalid")))
    except (UnicodeError, ValueError, RecursionError):
        raise CatalogError("catalog_invalid") from None
    if not isinstance(document, dict) or not isinstance(document.get("data"), list):
        raise CatalogError("catalog_invalid")
    entries = document["data"]
    if len(entries) > _MAX_MODELS:
        raise CatalogError("catalog_invalid")
    result = {}
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        model_id = entry.get("id")
        if (not isinstance(model_id, str) or len(model_id) > 128
                or model_id.casefold().startswith("openai/") or not _MODEL_ID.fullmatch(model_id)):
            continue
        if model_id in seen:
            result.pop(model_id, None)
            continue
        seen.add(model_id)
        architecture, pricing, capacity = entry.get("architecture"), entry.get("pricing"), entry.get("context_length")
        if (not isinstance(architecture, dict)
                or not isinstance(architecture.get("input_modalities"), list)
                or "text" not in architecture["input_modalities"]
                or not isinstance(architecture.get("output_modalities"), list)
                or "text" not in architecture["output_modalities"]
                or not isinstance(pricing, dict)
                or not {"prompt", "completion"}.issubset(pricing)
                or any(not _zero_price(value) for value in pricing.values())
                or type(capacity) is not int or not 0 < capacity <= 100_000_000):
            continue
        result[model_id] = CatalogModel(model_id, capacity)
    return tuple(sorted(result.values(), key=lambda model: model.model_id))


def fetch_catalog():
    """Fetch public metadata with a hard process deadline and bounded output."""
    try:
        env = {key: os.environ[key] for key in ('SYSTEMROOT', 'WINDIR') if key in os.environ}
        result = subprocess.run(
            [sys.executable, '-I', '-c', _FETCH_PROGRAM], capture_output=True,
            timeout=10, check=False, env=env,
        )
        if result.returncode != 0:
            raise CatalogError("catalog_unavailable")
    except (OSError, subprocess.SubprocessError):
        raise CatalogError("catalog_unavailable") from None
    return parse_catalog(result.stdout)


class CatalogCache:
    """Serve only fresh snapshots; perform at most one background fetch per process."""

    def __init__(self, *, ttl=60):
        self._ttl = ttl
        self._lock = threading.Lock()
        self._models = ()
        self._expires = 0.0
        self._fetching = False
        self._ready = threading.Event()

    def get(self, *, wait=False):
        with self._lock:
            if time.monotonic() < self._expires:
                return self._models
            if not self._fetching:
                self._fetching = True
                self._ready.clear()
                try:
                    threading.Thread(target=self._refresh, daemon=True).start()
                except Exception:
                    self._fetching = False
                    self._ready.set()
        if wait:
            self._ready.wait(12)
            with self._lock:
                if time.monotonic() < self._expires:
                    return self._models
        return ()

    def _refresh(self):
        try:
            models = fetch_catalog()
        except Exception:
            models = ()
        with self._lock:
            self._models = models
            self._expires = time.monotonic() + self._ttl
            self._fetching = False
            self._ready.set()


_catalog_cache = CatalogCache()


def cached_catalog(*, wait=False):
    """Return immediately; an empty result means unavailable or still loading."""
    return _catalog_cache.get(wait=wait)
