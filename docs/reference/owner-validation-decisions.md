# Owner validation decisions

## Product-first validation - 2026-11-14

The owner approved the product-first reorganization and constitution amendment. The controlling scope, exceptions and deferred replacements are in [product-first validation policy](product-first-validation.md). This supersedes conflicting earlier requirements to collect external evidence or perform independent audits before completing current implementation work. The benchmark waiver remains effective; enabled features still require applicable functional, security and recovery controls and proportionate checks.

## Benchmark waiver - 2026-11-11

Status: Accepted by explicit owner instruction: "quiero omitir los benchmarks". Applies prospectively to project performance/load and comparative model-quality benchmarks, including embedding, OCR, STT/TTS and release benchmark gates. Supersedes conflicting benchmark prerequisites in Q-23/Q-26/Q-29/Q-53, P-48/P-53, T186/T207/T215/T219/T237/T222 and derived proposals. Historical D3/D4 measurements and failures remain evidence; do not erase or rerun them as a prerequisite.

Given selected components, when implementing or accepting the enabled release, then omit numerical model-quality, throughput, latency, peak-resource benchmarking and comparative candidate scoring. Do not require RTF, CER/WER or retrieval-score benchmark thresholds to activate the owner's selected baseline. Document unmeasured quality, responsiveness, capacity and load behavior without claiming the removed thresholds passed. No automatic fallback is selected solely from an unmeasured benchmark gate.

Given functionality, security or recovery changes, when validating them, then retain the required application checks, authorization/cross-user denial, package/artifact/license review, bounded input handling, enforceable resource limits, heavy-job serialization, restart, backup/restore, corruption/interruption and rollback tests. Verify that enabled formats/languages produce usable outputs through functional cases; no numerical quality-scoring campaign is required. This waiver does not approve packages, service activation, external data sharing, deletion or production mutation. Missing functional/security/recovery evidence still keeps the corresponding acceptance scope open.

Constitution review: no amendment required. The constitution requires relevant checks, resource controls, backup/recovery validation and truthful evidence; it does not mandate comparative or numerical performance benchmarks. CONTRIBUTING's functional/security/data-change test obligations remain applicable. No production claim is created by this waiver.

Validation scope: documentation/configuration update only. See owner-attention for newly required DOCX/XLSX-to-PDF conversions and the separate R1/R2/R3 recovery proposals. No benchmark, VM operation, authentication or cryptographic implementation changed.
