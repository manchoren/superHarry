"""D4 offline synthetic CPU benchmark; no application imports or remote code."""

import argparse
from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import statistics
import threading
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("model_directory", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--e5", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[name] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    started = time.monotonic()
    report = {"status": "starting", "queue_wait_seconds": 0, "fixture_sha256": hashlib.sha256(args.fixture.read_bytes()).hexdigest()}
    # The launcher must provide a private network namespace with no routes.
    routes = Path("/proc/net/route").read_text().splitlines()
    assert len(routes) <= 1, "An offline network namespace is required"
    assert os.geteuid() != 0, "Run inference without root privileges"
    report["offline_network_namespace"] = True

    def save():
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        report["max_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        args.output.write_text(json.dumps(report, indent=2) + "\n")

    def guard():
        while True:
            time.sleep(.25)
            for line in Path("/proc/self/status").read_text().splitlines():
                if line.startswith("VmHWM:") and int(line.split()[1]) > 2 * 1024 * 1024:
                    report["status"] = "rss_limit_exceeded"
                    save()
                    os._exit(70)
            if time.monotonic() - started > 1800:
                report["status"] = "time_limit_exceeded"
                save()
                os._exit(71)

    save()
    threading.Thread(target=guard, daemon=True).start()
    import numpy as np
    import onnxruntime as ort
    from tokenizers import Tokenizer

    ort.disable_telemetry_events()
    report["runtime"] = {"onnxruntime": ort.__version__, "numpy": np.__version__, "providers": ort.get_available_providers()}
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    load_start = time.monotonic()
    model = args.model_directory / "onnx" / ("model.onnx" if args.e5 else "model_qint8_arm64.onnx")
    session = ort.InferenceSession(str(model), sess_options=options, providers=["CPUExecutionProvider"])
    report["cold_session_load_seconds"] = time.monotonic() - load_start
    report["session_providers"] = session.get_providers()
    assert report["session_providers"] == ["CPUExecutionProvider"]
    report["inputs"] = [{"name": v.name, "type": v.type, "shape": v.shape} for v in session.get_inputs()]
    report["outputs"] = [{"name": v.name, "type": v.type, "shape": v.shape} for v in session.get_outputs()]
    pooling = json.loads((args.model_directory / "1_Pooling/config.json").read_text())
    assert pooling["pooling_mode_mean_tokens"] is True
    assert not pooling.get("pooling_mode_cls_token") and not pooling.get("pooling_mode_max_tokens")
    tokenizer = Tokenizer.from_file(str(args.model_directory / "tokenizer.json"))
    configuration = json.loads((args.model_directory / "sentence_bert_config.json").read_text())
    max_length = configuration["max_seq_length"]
    assert max_length == (512 if args.e5 else 128)
    tokenizer.no_truncation()
    tokenizer.no_padding()
    truncated = 0

    def embed(text, is_query=False):
        nonlocal truncated
        prefix = ("query: " if is_query else "passage: ") if args.e5 else ""
        original = tokenizer.encode(prefix + text)
        if len(original.ids) > max_length:
            truncated += 1
            tokenizer.enable_truncation(max_length=max_length)
            encoded = tokenizer.encode(prefix + text)
            tokenizer.no_truncation()
        else:
            encoded = original
        values = {"input_ids": encoded.ids, "attention_mask": encoded.attention_mask, "token_type_ids": encoded.type_ids}
        feed = {}
        for node in session.get_inputs():
            assert node.name in values and node.type == "tensor(int64)", node.name
            feed[node.name] = np.asarray([values[node.name]], dtype=np.int64)
        outputs = session.run(None, feed)
        tokens = outputs[0]
        # Both pinned graphs must expose token embeddings, not guessed pooling.
        assert tokens.ndim == 3 and tokens.shape[0] == 1 and tokens.shape[2] == 384, tokens.shape
        mask = np.asarray(encoded.attention_mask, dtype=np.float32)[None, :, None]
        vector = (tokens * mask).sum(axis=1) / mask.sum(axis=1).clip(min=1)
        vector = vector[0]
        norm = np.linalg.norm(vector)
        assert np.isfinite(vector).all() and norm > 0
        return vector / norm

    fixture = json.loads(args.fixture.read_text())
    assert fixture["synthetic"] is True and len(fixture["memories"]) == 1000
    memories = fixture["memories"]
    index_started = time.monotonic()
    report["status"] = "indexing"
    vectors = []
    for index, memory in enumerate(memories):
        vectors.append(embed(memory["text"]))
        if (index + 1) % 50 == 0:
            report["indexed_records"] = index + 1
            save()
    vectors = np.asarray(vectors)
    report["index_seconds"] = time.monotonic() - index_started
    report["index_records_per_second"] = len(memories) / report["index_seconds"]
    report["vector_bytes"] = vectors.nbytes
    report["status"] = "querying"
    save()

    def search(query):
        vector = embed(query["text"], is_query=True)
        permitted = [i for i, m in enumerate(memories) if m["owner"] in (query["principal"], "global")]
        similarity = vectors[permitted] @ vector
        ranks = sorted(range(len(permitted)), key=lambda i: (-float(similarity[i]), memories[permitted[i]]["id"]))[:5]
        selected = [memories[permitted[i]] for i in ranks]
        assert all(m["owner"] in (query["principal"], "global") for m in selected)
        return [m["id"] for m in selected]

    for query in fixture["queries"][:10]:
        search(query)
    latencies = []
    scores = defaultdict(list)
    details = []
    for iteration in range(3):
        for query in fixture["queries"]:
            begin = time.monotonic()
            ranked = search(query)
            latencies.append(time.monotonic() - begin)
            if iteration == 0:
                relevant = set(query["relevant_ids"])
                recall = len(relevant.intersection(ranked)) / len(relevant)
                reciprocal = next((1 / i for i, identifier in enumerate(ranked, 1) if identifier in relevant), 0)
                for category in (query["category"], "overall"):
                    scores[category].append((recall, reciprocal))
                details.append({"query_id": query["id"], "ranked_ids": ranked, "recall_at_5": recall, "reciprocal_rank_at_5": reciprocal})
    report["metrics"] = {k: {"recall_at_5": statistics.mean(v[0] for v in values), "mrr_at_5": statistics.mean(v[1] for v in values)} for k, values in scores.items()}
    report["warmup_queries"] = 10
    report["timed_queries"] = len(latencies)
    report["warm_query_p50_seconds"] = statistics.median(latencies)
    report["warm_query_p95_seconds"] = sorted(latencies)[math.ceil(.95 * len(latencies)) - 1]
    report["truncations"] = truncated
    report["details"] = details
    report["diagnostic_gates"] = {
        "lexical_recall": report["metrics"]["lexical"]["recall_at_5"] == 1,
        "cross_language_recall": report["metrics"]["cross_language"]["recall_at_5"] >= .8,
        "paraphrase_recall": report["metrics"]["paraphrase"]["recall_at_5"] >= .8,
        "overall_mrr": report["metrics"]["overall"]["mrr_at_5"] >= .75,
        "warm_latency": report["warm_query_p95_seconds"] <= 2,
    }
    report["status"] = "completed"
    report["limitations"] = "Synthetic diagnostic only; no live memory, production RBAC, disk index encryption/deletion, gateway integration or release acceptance. Queue wait is zero for direct isolated execution. No 10,000-record scale test."
    save()
    print(json.dumps({k: v for k, v in report.items() if k != "details"}, indent=2))


if __name__ == "__main__":
    main()
