# T207 - OCR evaluation proposal

Current validation policy (owner, 2026-11-11): [future benchmarks waived](owner-validation-decisions.md#benchmark-waiver---2026-11-11). Numerical/comparative benchmark gates below are superseded; historical results remain evidence. Functional, security, resource-enforcement, language/format smoke checks and recovery tests remain required. No package or deployment approval is implied.

Date: 2026-11-11. Status: Tesseract accepted as the sole initial evaluation candidate by the owner on 2026-11-11; production selection and installation remain unapproved. T207 depends on T206 and T237; T237 depends on T225. This document prepares the decision, not completion of those tasks.

## Decision to make

Evaluate Tesseract offline on the target ARM64 VM against frozen Spanish/English quality, latency and memory gates. If Tesseract fails or performs poorly, RapidOCR is a reserved alternative for separate review and evaluation; it is not part of the initial benchmark or an automatic runtime fallback. If no evaluated candidate passes, select none and review the requirements. OCR produces untrusted text, not image understanding.

| Candidate | Evaluation profile | Open questions |
|---|---|---|
| Tesseract | CLI with `spa+eng` language data, initially `tessdata_fast`; record segmentation mode and all preprocessing. | Pin the Debian engine, dependencies and both language artifacts; establish whether this profile handles the fixture layouts. |
| RapidOCR (reserved alternative) | CPU ONNX Runtime with a Latin-script recognition model, detection and any orientation model required by the selected configuration. | Verify exact Latin model's Spanish accents, English coverage, model files and dictionary; pin runtime, detection, recognition and optional classification artifacts and all dependencies for ARM64. Default Chinese/English recognition is insufficient evidence for Spanish. |

Upstream [Tesseract data documentation](https://github.com/tesseract-ocr/tessdoc/blob/main/Data-Files.md) describes `tessdata_fast` as a speed-oriented choice. [RapidOCR's model list](https://github.com/RapidAI/RapidOCRDocs/blob/main/docs/model_list.md) lists a Latin-script model; its [installation guide](https://github.com/RapidAI/RapidOCRDocs/blob/main/docs/install_usage/rapidocr/install.en.md) states that ONNX Runtime must be installed separately with recent versions and that some models can be downloaded automatically. Pin and stage every required artifact and deny network access during inference; do not treat the presence of a model in a list as proof of Spanish accuracy. Both projects describe Apache-2.0 licensing, including applicable upstream models, but verify the license and notices of each selected artifact and dependency ([Tesseract](https://github.com/tesseract-ocr/tessdoc/blob/main/Installation.md), [RapidOCR](https://github.com/RapidAI/RapidOCR)).

## Proposed frozen evaluation

Under T237, create and version at least 60 synthetic, rights-cleared images and independently checked UTF-8 transcriptions: 20 Spanish, 20 English and 20 mixed-language. Include accents, ñ, punctuation, numbers, small print, different fonts, screenshots, photographed documents, mild skew, uneven illumination and multi-line layouts; record category and image dimensions. Include blank images and a few clearly labeled challenging cases. Avoid personal data. Reserve a documented holdout subset and freeze image and transcription hashes, ordering, preprocessing and scoring before tuning or measuring. Do not use these examples as a claim of production representativeness; extend the corpus when actual supported inputs are defined.

Score case-sensitive character error rate (CER) and word error rate (WER) as edit distance divided by the reference length, after applying the same documented Unicode NFC and line-ending normalization to reference and output. Do not strip accents, punctuation or case. Report aggregate and per-language scores, per-image results, blank-image hallucinations, failures and reading-order errors; define whitespace/tokenization in the frozen scorer. Report critical tokens such as amounts and identifiers separately, without presenting OCR as reliable for high-stakes transcription.

Proposed starting gates, requiring agreement and freezing under T237 before measurements, not existing accepted requirements:

| Gate | Proposed threshold |
|---|---|
| Quality | Aggregate CER ≤ 5% and CER ≤ 8% for each Spanish, English and mixed group; blank cases produce no text. Report WER and challenging cases separately. |
| Latency | Warm p95 ≤ 10 seconds per image and cold-start p95 ≤ 30 seconds, including process/model startup and image decoding, excluding queue time. |
| Memory | Peak incremental process-tree memory ≤ 512 MiB above the idle test baseline; also report absolute peak and VM available memory. |
| Reliability | All supported cases terminate within 60 seconds, with explicit errors rather than silently empty results; no network access during inference. |

These are initial evaluation proposals, not verified VM capacity or release acceptance. Confirm workload, image-size bounds, operating headroom and thresholds before freezing; use the most restrictive applicable resource governor limits. If a measurement or gate cannot be established, mark it unavailable and do not declare a pass.

## VM protocol

1. Confirm the target guest is healthy and record OS, architecture, CPU allocation, RAM, disk, Python, current service workload and baseline available memory. Use a disposable isolated VM copy and synthetic inputs, with no production database, service changes or credentials. Do not proceed when guest state is ambiguous.
2. Before requesting installation approval, produce an exact manifest with official source, versions or immutable revisions, SHA-256, download and installed sizes, licenses, direct dependencies, ARM64 compatibility, applicable advisories and unresolved findings. Include OS packages, Python wheels, language data and every OCR model/dictionary. Review package policy and scoped installation approval separately. Do not assume existing authorizations cover these artifacts.
3. Use bounded input files and documented preprocessing; if RapidOCR is later evaluated, use the same inputs and common preprocessing for both; document engine-specific configuration, thread counts, CPU limits and any differences. Record model-load and inference settings; disable implicit downloads. Only one heavy job runs at a time, consistent with the resource governor.
4. For the Tesseract profile, measure at least three fresh-process cold runs and three warmed passes across the frozen corpus. If RapidOCR is later approved for comparison, repeat the frozen protocol for both profiles, alternating candidate order. Use a monotonic clock and a documented sampler or cgroup covering all child processes; report p50/p95, per-run peak and baseline, queue delay separately, failure count and versions/hashes. Report sample sizes and measurement limitations. Repeat under a separately predefined representative background workload if the idle test passes; report both conditions separately.
5. Store sanitized machine-readable outputs and a reproducible summary with fixture/configuration hashes. Remove the disposable workspace after evidence capture, and verify production remains untouched. Test malicious OCR text and isolation with the eventual integrated pipeline; this benchmark alone does not establish T206 hygiene or security acceptance.

## Selection rule and result record

Accept Tesseract for production only after it passes every frozen gate and artifact, architecture, security and integration requirements. If it fails or performs poorly, retain the evidence and consider RapidOCR as an alternative: prepare its exact artifacts and isolated scope for separate approval, then evaluate it using the same frozen protocol. If neither passes, select neither; revise the profile or requirements before retesting. Any candidate change requires a new pinned profile and the same holdout protocol.

| Result | Tesseract | RapidOCR |
|---|---|---|
| Artifact manifest / approval | Pending | Pending |
| CER / WER by language, blank cases | Not measured | Not measured |
| Cold / warm p50 and p95; queue delay | Not measured | Not measured |
| Peak incremental and absolute memory | Not measured | Not measured |
| Gate outcome and decision | Pending | Pending |

This proposal authorizes no download, installation, VM modification, production integration or release. The owner accepted Tesseract as the initial candidate and reserved RapidOCR as an alternative on 2026-11-11. Owner review of exact artifacts and isolated test scope precedes installation; production acceptance follows actual results. T207 remains pending.
