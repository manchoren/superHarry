"""Run a synthetic FTS5 reference benchmark; no application or model imports."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import statistics
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--timing-repeats", type=int, default=1)
    parser.add_argument("--warmup", type=int, default=0)
    args = parser.parse_args()
    raw = args.fixture.read_bytes()
    fixture = json.loads(raw)
    assert fixture["synthetic"] is True
    memories = fixture["memories"]
    ids = {row["id"] for row in memories}
    assert len(ids) == len(memories)
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE VIRTUAL TABLE memory USING fts5(id UNINDEXED, owner UNINDEXED, content, tokenize='unicode61 remove_diacritics 2')")
    connection.executemany("INSERT INTO memory VALUES (?, ?, ?)", [(m["id"], m["owner"], m["text"]) for m in memories])
    scores = defaultdict(list)
    durations = []
    details = []
    assert args.timing_repeats >= 1 and args.warmup >= 0
    def search(query):
        terms = re.findall(r"\w+", query["text"], re.UNICODE)
        expression = " OR ".join('"' + term + '"' for term in terms)
        return connection.execute(
            "SELECT id, owner FROM memory WHERE memory MATCH ? AND owner IN (?, 'global') ORDER BY bm25(memory), id LIMIT 5",
            (expression, query["principal"]),
        ).fetchall() if expression else []
    for i in range(args.warmup):
        search(fixture["queries"][i % len(fixture["queries"])])
    for query in fixture["queries"]:
        relevant = set(query["relevant_ids"])
        assert relevant and relevant <= ids
        # Fixture queries are data; quote each term, never interpret FTS syntax.
        terms = re.findall(r"\w+", query["text"], re.UNICODE)
        expression = " OR ".join('"' + term + '"' for term in terms)
        start = time.perf_counter()
        ranked = connection.execute(
            "SELECT id, owner FROM memory WHERE memory MATCH ? AND owner IN (?, 'global') ORDER BY bm25(memory), id LIMIT 5",
            (expression, query["principal"]),
        ).fetchall() if expression else []
        durations.append((time.perf_counter() - start) * 1000)
        assert all(owner in (query["principal"], "global") for _, owner in ranked)
        retrieved = [identifier for identifier, _ in ranked]
        recall = len(relevant.intersection(retrieved)) / len(relevant)
        reciprocal = next((1 / rank for rank, identifier in enumerate(retrieved, 1) if identifier in relevant), 0)
        scores[query["category"]].append((recall, reciprocal))
        scores["overall"].append((recall, reciprocal))
        details.append({"query_id": query["id"], "ranked_ids": retrieved, "recall_at_5": recall, "reciprocal_rank_at_5": reciprocal})
    for _ in range(args.timing_repeats - 1):
        for query in fixture["queries"]:
            start = time.perf_counter()
            search(query)
            durations.append((time.perf_counter() - start) * 1000)
    result = {
        "fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "sqlite_version": sqlite3.sqlite_version,
        "method": "FTS5 unicode61 OR terms, BM25; SQL owner filter; no stemming or translation",
        "query_count": len(details),
        "warmup_queries": args.warmup,
        "timed_queries": len(durations),
        "metrics": {category: {"recall_at_5": statistics.mean(v[0] for v in values), "mrr_at_5": statistics.mean(v[1] for v in values)} for category, values in scores.items()},
        "query_latency_p95_ms": sorted(durations)[max(0, int(len(durations) * .95 + .999) - 1)],
        "details": details,
        "limitations": "Host-only tiny synthetic baseline; not a target-VM benchmark or application authorization test. SQL filtering occurs before return but BM25 corpus statistics include fixture distractors; production isolation still needs design and tests.",
    }
    connection.close()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
