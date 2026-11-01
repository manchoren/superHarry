#!/usr/bin/env python3
"""Read-only cross-check of selected npm SLSA bundles against Rekor v1."""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import urllib.parse
import urllib.request


USER_AGENT = "superHarry-T014-static-review/1.0"
PACKAGES = (
    ("argon2", "0.45.1"),
    ("otpauth", "9.5.2"),
    ("@noble/hashes", "2.4.0"),
)


def get_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def decode_hash(value: str) -> bytes:
    if len(value) == 64:
        try:
            return bytes.fromhex(value)
        except ValueError:
            pass
    return base64.b64decode(value, validate=True)


def rekor_proof_matches(body: bytes, proof: dict) -> bool:
    index = int(proof["logIndex"])
    last_node = int(proof["treeSize"]) - 1
    node = hashlib.sha256(b"\x00" + body).digest()

    for sibling_value in proof["hashes"]:
        sibling = decode_hash(sibling_value)
        if index & 1 or index == last_node:
            node = hashlib.sha256(b"\x01" + sibling + node).digest()
            while (index & 1) == 0 and index != 0:
                index >>= 1
                last_node >>= 1
        else:
            node = hashlib.sha256(b"\x01" + node + sibling).digest()
        index >>= 1
        last_node >>= 1

    return last_node == 0 and node == decode_hash(proof["rootHash"])


def lookup_entry(log_index: str) -> dict:
    query = urllib.parse.urlencode({"logIndex": log_index})
    entries = get_json(f"https://rekor.sigstore.dev/api/v1/log/entries?{query}")
    if len(entries) != 1:
        raise ValueError(f"Expected one Rekor entry for logIndex {log_index}")
    return next(iter(entries.values()))


def main() -> None:
    results = []
    for name, version in PACKAGES:
        encoded_name = urllib.parse.quote(name, safe="").replace("%2F", "%2f")
        metadata = get_json(
            "https://registry.npmjs.org/-/npm/v1/attestations/"
            f"{encoded_name}@{version}"
        )
        attestation = next(
            item
            for item in metadata["attestations"]
            if item.get("predicateType") == "https://slsa.dev/provenance/v1"
        )
        tlog_entry = attestation["bundle"]["verificationMaterial"]["tlogEntries"][0]
        body = base64.b64decode(tlog_entry["canonicalizedBody"], validate=True)
        entry_index = str(tlog_entry["logIndex"])
        entry = lookup_entry(entry_index)
        live_body = base64.b64decode(entry["body"], validate=True)
        proof = entry["verification"]["inclusionProof"]
        proof_index = str(proof["logIndex"])
        proof_entry = lookup_entry(proof_index)
        proof_body = base64.b64decode(proof_entry["body"], validate=True)
        bundle_proof = tlog_entry["inclusionProof"]

        results.append(
            {
                "name": name,
                "version": version,
                "bundle_log_index": entry_index,
                "bundle_proof_log_index": str(
                    bundle_proof["logIndex"]
                ),
                "bundle_proof_tree_size": str(bundle_proof["treeSize"]),
                "bundle_proof_root_hash": bundle_proof["rootHash"],
                "bundle_merkle_path_recomputes_to_bundle_root": rekor_proof_matches(
                    body, bundle_proof
                ),
                "live_entry_log_index": str(entry["logIndex"]),
                "live_body_matches_bundle_canonicalized_body": live_body == body,
                "live_entry_canonicalized_body_sha256": hashlib.sha256(
                    live_body
                ).hexdigest(),
                "live_proof_log_index": proof_index,
                "live_proof_index_resolves_to_same_body": proof_body == live_body,
                "live_merkle_path_body_recomputes_to_root": rekor_proof_matches(
                    live_body, proof
                ),
                "live_proof_index_matches_entry_index": proof_index
                == str(entry["logIndex"]),
                "live_log_id": entry["logID"],
                "live_proof_tree_size": str(proof["treeSize"]),
                "live_proof_root_hash": proof["rootHash"],
            }
        )

    print(
        json.dumps(
            {
                "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "results": results,
                "limitations": [
                    "This script does not authenticate the Fulcio or Rekor trust root.",
                    "It does not verify signed checkpoints or signed entry timestamps.",
                    "A recomputed Merkle root does not resolve an index/body mismatch.",
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
