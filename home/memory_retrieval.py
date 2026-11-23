"""Bounded memory retrieval orchestration.

Semantic inference is deliberately injected by the caller.  This module keeps
authorization outside any model adapter and provides a deterministic keyword
fallback for the product-first local path.
"""

import re
import unicodedata

from home.models import MemoryRecord
from home.memory_access import (
    MemoryAccessUnavailable,
    MemoryRetrievalAuthorization,
    read_records_for_retrieval,
)


MAX_QUERY_CHARS = 512
MAX_RESULTS = 10
MAX_CONTEXT_BYTES = 8192
_TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)


class MemoryRetrievalUnavailable(Exception):
    """Retrieval could not produce an authorized result."""


def _tokens(value):
    normalized = unicodedata.normalize("NFKD", value).casefold()
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return tuple(_TOKEN_RE.findall(normalized))


def _keyword_results(records, query, limit):
    query_tokens = set(_tokens(query))
    if not query_tokens:
        return []
    ranked = []
    for record in records:
        content_tokens = set(_tokens(record.content))
        overlap = len(query_tokens & content_tokens)
        if overlap:
            ranked.append((-overlap, record.created_at, str(record.pk), record))
    ranked.sort(key=lambda item: item[:3])
    return [item[-1] for item in ranked[:limit]]


def retrieve_memory_records(*, user, query, semantic_search=None, limit=5):
    """Return authorized records, preferring injected semantic search.

    The semantic adapter receives only the already-authorized queryset records.
    Any adapter exception or empty result uses the bounded keyword fallback;
    malformed adapter output is treated as unavailable rather than trusted.
    """
    if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY_CHARS:
        raise MemoryRetrievalUnavailable("memory_retrieval_unavailable")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_RESULTS:
        raise MemoryRetrievalUnavailable("memory_retrieval_unavailable")

    records = list(MemoryRecord.objects.visible_to(user).order_by("created_at", "id"))
    if semantic_search is not None:
        try:
            semantic = semantic_search(records, query, limit)
            authorized_instances = {id(record) for record in records}
            if isinstance(semantic, (list, tuple)) and all(
                    isinstance(record, MemoryRecord) and id(record) in authorized_instances
                    for record in semantic):
                unique = list(dict.fromkeys(semantic))
                if unique:
                    return unique[:limit], "semantic"
        except Exception:
            pass
    return _keyword_results(records, query, limit), "keyword"


def retrieve_authorized_memory_records(
    *, authorization, query, semantic_search=None, limit=5, charge_usage
):
    """Retrieve bounded records through the server-owned access boundary."""
    if not isinstance(authorization, MemoryRetrievalAuthorization) or not callable(charge_usage):
        raise MemoryRetrievalUnavailable("memory_retrieval_unavailable")
    try:
        from django.contrib.auth import get_user_model
        principal = get_user_model()._default_manager.get(
            pk=authorization.user_id, is_active=True,
        )
        if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY_CHARS:
            raise MemoryRetrievalUnavailable("memory_retrieval_unavailable")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_RESULTS:
            raise MemoryRetrievalUnavailable("memory_retrieval_unavailable")
        bounded, context_bytes = [], len(query.encode("utf-8"))
        for record in MemoryRecord.objects.visible_to(principal).order_by("created_at", "id"):
            size = len(record.content.encode("utf-8"))
            if context_bytes + size <= MAX_CONTEXT_BYTES:
                bounded.append(record)
                context_bytes += size
        semantic = None
        if semantic_search is not None:
            try:
                semantic = semantic_search(bounded, query, limit)
            except Exception:
                semantic = None
        authorized_instances = {id(record) for record in bounded}
        if (isinstance(semantic, (list, tuple))
                and all(isinstance(record, MemoryRecord) and id(record) in authorized_instances
                        for record in semantic)):
            selected = list(dict.fromkeys(semantic))[:limit]
            mode = "semantic" if selected else "keyword"
        else:
            selected, mode = _keyword_results(bounded, query, limit), "keyword"
        usage = len(query.encode("utf-8")) + sum(
            len(record.content.encode("utf-8")) for record in selected
        )
        if charge_usage(usage) is not True:
            raise MemoryRetrievalUnavailable("memory_retrieval_unavailable")
        records = read_records_for_retrieval(
            authorization, [record.pk for record in selected]
        ) if selected else []
        return records, mode, usage
    except (MemoryAccessUnavailable, MemoryRetrievalUnavailable):
        raise MemoryRetrievalUnavailable("memory_retrieval_unavailable") from None
    except get_user_model().DoesNotExist:
        raise MemoryRetrievalUnavailable("memory_retrieval_unavailable") from None
