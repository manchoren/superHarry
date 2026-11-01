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


def openssl_signature_verifies(
    public_key_pem: bytes, message: bytes, signature: bytes
) -> bool:
    with tempfile.TemporaryDirectory(prefix="t014-openssl-signature-") as temp_dir:
        directory = Path(temp_dir)
        key_path = directory / "key.pem"
        message_path = directory / "message.bin"
        signature_path = directory / "signature.der"
        key_path.write_bytes(public_key_pem)
        message_path.write_bytes(message)
        signature_path.write_bytes(signature)
        result = subprocess.run(
            [
                "openssl",
                "dgst",
                "-sha256",
                "-verify",
                str(key_path),
                "-signature",
                str(signature_path),
                str(message_path),
            ],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0


def public_key_pem(public_key_der: bytes) -> bytes:
    with tempfile.TemporaryDirectory(prefix="t014-public-key-") as temp_dir:
        directory = Path(temp_dir)
        der_path = directory / "key.der"
        pem_path = directory / "key.pem"
        der_path.write_bytes(public_key_der)
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
        return pem_path.read_bytes()


def certificate_public_key(certificate_der: bytes) -> tuple[bytes, bytes]:
    with tempfile.TemporaryDirectory(prefix="t014-leaf-certificate-") as temp_dir:
        directory = Path(temp_dir)
        certificate_path = directory / "certificate.der"
        certificate_pem_path = directory / "certificate.pem"
        public_key_path = directory / "public-key.pem"
        certificate_path.write_bytes(certificate_der)
        subprocess.run(
            [
                "openssl",
                "x509",
                "-inform",
                "DER",
                "-in",
                str(certificate_path),
                "-out",
                str(certificate_pem_path),
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "openssl",
                "x509",
                "-in",
                str(certificate_pem_path),
                "-pubkey",
                "-noout",
                "-out",
                str(public_key_path),
            ],
            check=True,
            capture_output=True,
        )
        certificate_info = subprocess.run(
            [
                "openssl",
                "x509",
                "-in",
                str(certificate_pem_path),
                "-noout",
                "-ext",
                "subjectAltName",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        return public_key_path.read_bytes(), certificate_info


def verify_fulcio_chain(
    certificate_der: bytes, trusted_root: dict, integrated_time: int
) -> tuple[bool, str]:
    check_time = dt.datetime.fromtimestamp(
        integrated_time, tz=dt.timezone.utc
    )
    authorities = [
        authority
        for authority in trusted_root["certificateAuthorities"]
        if authority.get("uri") == "https://fulcio.sigstore.dev"
        and dt.datetime.fromisoformat(
            authority["validFor"]["start"].replace("Z", "+00:00")
        )
        <= check_time
        and (
            "end" not in authority["validFor"]
            or check_time
            <= dt.datetime.fromisoformat(
                authority["validFor"]["end"].replace("Z", "+00:00")
            )
        )
    ]
    if not authorities:
        raise ValueError("No Fulcio trust anchor valid at integratedTime")
    authority = max(
        authorities,
        key=lambda item: len(item["certChain"]["certificates"]),
    )
    chain = [
        base64.b64decode(item["rawBytes"], validate=True)
        for item in authority["certChain"]["certificates"]
    ]
    if len(chain) < 2:
        raise ValueError("Expected Fulcio intermediate and root certificates")

    with tempfile.TemporaryDirectory(prefix="t014-fulcio-chain-") as temp_dir:
        directory = Path(temp_dir)
        leaf_der_path = directory / "leaf.der"
        leaf_pem_path = directory / "leaf.pem"
        root_der_path = directory / "root.der"
        root_pem_path = directory / "root.pem"
        intermediates_path = directory / "intermediates.pem"
        leaf_der_path.write_bytes(certificate_der)
        root_der_path.write_bytes(chain[-1])
        subprocess.run(
            [
                "openssl",
                "x509",
                "-inform",
                "DER",
                "-in",
                str(leaf_der_path),
                "-out",
                str(leaf_pem_path),
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "openssl",
                "x509",
                "-inform",
                "DER",
                "-in",
                str(root_der_path),
                "-out",
                str(root_pem_path),
            ],
            check=True,
            capture_output=True,
        )
        intermediate_pems = []
        for index, intermediate_der in enumerate(chain[:-1]):
            der_path = directory / f"intermediate-{index}.der"
            pem_path = directory / f"intermediate-{index}.pem"
            der_path.write_bytes(intermediate_der)
            subprocess.run(
                [
                    "openssl",
                    "x509",
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
            intermediate_pems.append(pem_path.read_bytes())
        intermediates_path.write_bytes(b"".join(intermediate_pems))
        verification = subprocess.run(
            [
                "openssl",
                "verify",
                "-attime",
                str(integrated_time),
                "-purpose",
                "any",
                "-CAfile",
                str(root_pem_path),
                "-untrusted",
                str(intermediates_path),
                str(leaf_pem_path),
            ],
            capture_output=True,
            text=True,
        )
        info = subprocess.run(
            [
                "openssl",
                "x509",
                "-inform",
                "DER",
                "-in",
                str(leaf_der_path),
                "-noout",
                "-dates",
                "-issuer",
                "-subject",
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return verification.returncode == 0, info


def canonicalize_set_payload(entry: dict) -> bytes:
    payload = {
        "body": entry["body"],
        "integratedTime": entry["integratedTime"],
        "logID": entry["logID"],
        "logIndex": entry["logIndex"],
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


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
        set_signature = base64.b64decode(
            entry["verification"]["signedEntryTimestamp"], validate=True
        )
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
        log_public_key_pem = public_key_pem(log_public_key)
        certificate_der = base64.b64decode(
            attestation["bundle"]["verificationMaterial"]["certificate"][
                "rawBytes"
            ],
            validate=True,
        )
        leaf_public_key, certificate_identity = certificate_public_key(
            certificate_der
        )
        envelope = attestation["bundle"]["dsseEnvelope"]
        payload_type = envelope["payloadType"].encode("utf-8")
        payload = base64.b64decode(envelope["payload"], validate=True)
        pae = (
            b"DSSEv1 "
            + str(len(payload_type)).encode("ascii")
            + b" "
            + payload_type
            + b" "
            + str(len(payload)).encode("ascii")
            + b" "
            + payload
        )
        dsse_signatures = [
            openssl_signature_verifies(
                leaf_public_key,
                pae,
                base64.b64decode(signature["sig"], validate=True),
            )
            for signature in envelope["signatures"]
        ]
        if not dsse_signatures or not all(dsse_signatures):
            raise ValueError(f"DSSE signature verification failed for {name}")
        integrated_time = int(tlog_entry["integratedTime"])
        chain_verified, certificate_info = verify_fulcio_chain(
            certificate_der, trusted_root, integrated_time
        )
        if not chain_verified:
            raise ValueError(f"Fulcio chain verification failed for {name}")
        set_payload = canonicalize_set_payload(entry)
        set_verified = openssl_signature_verifies(
            log_public_key_pem, set_payload, set_signature
        )
        bundle_set_signature = base64.b64decode(
            tlog_entry["inclusionPromise"]["signedEntryTimestamp"],
            validate=True,
        )
        bundle_set_verified = openssl_signature_verifies(
            log_public_key_pem, set_payload, bundle_set_signature
        )
        if not set_verified or not bundle_set_verified:
            raise ValueError(f"Rekor signed-entry timestamp failed for {name}")
        bundle_merkle_verified = rekor_proof_matches(body, bundle_proof)
        bundle_checkpoint_verified = verify_checkpoint(
            bundle_proof["checkpoint"], log_public_key
        )
        live_body_verified = live_body == body
        live_merkle_verified = rekor_proof_matches(live_body, proof)
        live_checkpoint_verified = verify_checkpoint(
            proof["checkpoint"], log_public_key
        )
        if not all(
            (
                bundle_merkle_verified,
                bundle_checkpoint_verified,
                live_body_verified,
                live_merkle_verified,
                live_checkpoint_verified,
            )
        ):
            raise ValueError(f"Rekor proof or checkpoint verification failed for {name}")

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
                "bundle_merkle_path_recomputes_to_bundle_root": (
                    bundle_merkle_verified
                ),
                "bundle_checkpoint_signature_verified_with_published_log_key": (
                    bundle_checkpoint_verified
                ),
                "dsse_signatures_verified_with_embedded_leaf_certificate": (
                    all(dsse_signatures)
                ),
                "fulcio_certificate_chain_valid_at_integrated_time": chain_verified,
                "fulcio_trust_root_authenticated": False,
                "fulcio_leaf_certificate_identity": certificate_identity.strip(),
                "fulcio_leaf_certificate_info": certificate_info,
                "live_entry_log_index": str(entry["logIndex"]),
                "live_signed_entry_timestamp_verified_with_published_log_key": (
                    set_verified
                ),
                "bundle_signed_entry_timestamp_verified_with_published_log_key": (
                    bundle_set_verified
                ),
                "live_body_matches_bundle_canonicalized_body": live_body_verified,
                "live_entry_canonicalized_body_sha256": hashlib.sha256(
                    live_body
                ).hexdigest(),
                "live_inclusion_proof_log_index": str(proof["logIndex"]),
                "entry_log_index_is_virtual_index": True,
                "inclusion_proof_log_index_is_leaf_index": str(
                    proof["logIndex"]
                ),
                "live_merkle_path_body_recomputes_to_root": live_merkle_verified,
                "live_checkpoint_signature_verified_with_published_log_key": (
                    live_checkpoint_verified
                ),
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
                    "Fulcio revocation and project-specific workflow identity policy are not verified here.",
                    "Rekor entry logIndex is the virtual index; inclusionProof.logIndex is the Merkle leaf index.",
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
