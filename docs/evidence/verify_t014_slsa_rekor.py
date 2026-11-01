#!/usr/bin/env python3
"""Read-only cross-check of selected npm SLSA bundles against Rekor v1."""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path


USER_AGENT = "superHarry-T014-static-review/1.0"
TRUSTED_ROOT_URL = (
    "https://raw.githubusercontent.com/sigstore/root-signing/main/targets/"
    "trusted_root.json"
)
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


def get_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def decode_hash(value: str) -> bytes:
    if len(value) == 64:
        try:
            return bytes.fromhex(value)
        except ValueError:
            pass
    return base64.b64decode(value, validate=True)


def verify_checkpoint(checkpoint: str | dict, public_key: bytes) -> bool:
    envelope = checkpoint["envelope"] if isinstance(checkpoint, dict) else checkpoint
    encoded = envelope.encode("utf-8")
    signed_text, signature_block = encoded.rsplit(b"\n\n", maxsplit=1)
    signature_line = signature_block.splitlines()[0]
    prefix, name, encoded_signature = signature_line.split(b" ", maxsplit=2)
    if prefix != "—".encode("utf-8") or name != b"rekor.sigstore.dev":
        raise ValueError("Unexpected Rekor checkpoint signature framing")
    signature = base64.b64decode(encoded_signature, validate=True)
    if signature[:4] != hashlib.sha256(public_key).digest()[:4]:
        raise ValueError("Checkpoint signing-key hint does not match the key")

    with tempfile.TemporaryDirectory(prefix="t014-rekor-checkpoint-") as temp_dir:
        directory = Path(temp_dir)
        der_path = directory / "key.der"
        pem_path = directory / "key.pem"
        signature_path = directory / "signature.der"
        message_path = directory / "checkpoint.txt"
        der_path.write_bytes(public_key)
        signature_path.write_bytes(signature[4:])
        message_path.write_bytes(signed_text + b"\n")
        subprocess.run(
            [
                "openssl",
                "pkey",
                "-pubin",
                "-inform",
                "DER",
                "-in",
                str(der_path),
                "-out",
                str(pem_path),
            ],
            check=True,
            capture_output=True,
        )
        result = subprocess.run(
            [
                "openssl",
                "dgst",
                "-sha256",
                "-verify",
                str(pem_path),
                "-signature",
                str(signature_path),
                str(message_path),
            ],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0


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
    trusted_root_bytes = get_bytes(TRUSTED_ROOT_URL)
    trusted_root = json.loads(trusted_root_bytes)
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
        log_key = next(
            item
            for item in trusted_root["tlogs"]
            if item["logId"]["keyId"] == tlog_entry["logId"]["keyId"]
        )
        log_public_key = base64.b64decode(
            log_key["publicKey"]["rawBytes"], validate=True
        )
        log_id_bytes = base64.b64decode(
            log_key["logId"]["keyId"], validate=True
        )
        if hashlib.sha256(log_public_key).digest() != log_id_bytes:
            raise ValueError(f"Rekor key ID does not match public key for {name}")

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
                "bundle_checkpoint_signature_verified_with_published_log_key": (
                    verify_checkpoint(bundle_proof["checkpoint"], log_public_key)
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
                "live_checkpoint_signature_verified_with_published_log_key": (
                    verify_checkpoint(proof["checkpoint"], log_public_key)
                ),
                "live_proof_index_matches_entry_index": proof_index
                == str(entry["logIndex"]),
                "live_log_id": entry["logID"],
                "live_proof_tree_size": str(proof["treeSize"]),
                "live_proof_root_hash": proof["rootHash"],
                "log_key_id_matches_published_key": True,
            }
        )

    print(
        json.dumps(
            {
                "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "trusted_root_source": TRUSTED_ROOT_URL,
                "trusted_root_sha256": hashlib.sha256(
                    trusted_root_bytes
                ).hexdigest(),
                "results": results,
                "limitations": [
                    "The fetched Sigstore trusted-root file is not TUF-authenticated here.",
                    "Checkpoint signatures are verified mathematically against the published Rekor key only.",
                    "The Fulcio certificate chain and signed entry timestamps are not verified here.",
                    "A recomputed Merkle root does not resolve an index/body mismatch.",
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
