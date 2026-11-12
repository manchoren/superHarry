# T186 - Semantic memory retrieval evaluation

Current validation policy (owner, 2026-11-11): [future benchmarks waived](owner-validation-decisions.md#benchmark-waiver---2026-11-11). Numerical/comparative benchmark gates below are superseded; historical results remain evidence. Functional, security, resource-enforcement, language/format smoke checks and recovery tests remain required. No package or deployment approval is implied.

Date: 2026-11-11. Assignee: Codex. Model: Unknown. Scope: synthetic fixture preparation, keyword reference and owner-approved isolated model evaluation. T186 implementation remains dependent on T183/T237; T237 depends on T225.
Constitution SHA-256: `640c85a00d537e01fe446ac4516cb09cb53df2acdac493615fb5e72bdd792e64`.

## Owner model selection - 2026-11-11

Status: Selected by the owner ("creo que MiniLM es la eleccion correcta"). Use `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`, with the tested `onnx/model_qint8_arm64.onnx` artifact (SHA-256 `783fea82d71a58179b830a4dbd2d58447e640609e98eedf9ffa12622d375a672`) as the T186 embedding model baseline. Keep tokenizer/config identities pinned to the existing manifest; preserve its tested 128-token limit, masked mean pooling and normalized 384-dimensional vectors.

Given further T186 implementation and T237 evaluation, when choosing the embedding model, then use this selected baseline and retain keyword fallback under Q-23. Do not repeat the model-selection question for this scope. A different model, revision or quantization is a separate selection change.

Production serving location and omniroute compatibility remain open; this selection does not authorize a new direct production model path, external data sharing or service activation. Complete held-out/security/resource validation, T183 memory integration, index encryption/deletion and applicable deployment gates before enabling the feature. D4's runtime dependency approval remains scoped to its isolated experiment. No constitution amendment is required; T186 stays open.

## Candidate evidence

| Candidate | Verified metadata and purpose | Evaluation caveat |
|---|---|---|
| intfloat/multilingual-e5-small | MIT model card; 384 dimensions; retrieval-oriented, requires query/passage prefixes as documented (use the actual `query: ` and `passage: ` prefixes). Pinned upstream ONNX model: 470,268,510 bytes. | Use masked mean pooling and normalization as documented, max 512 tokens. Do not substitute an x86-named quantized artifact for an ARM64 validation claim. |
| sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 | Apache-2.0 model card; 384 dimensions, multilingual sentence similarity. Pinned upstream ARM64 qint8 ONNX artifact: 118,412,398 bytes. | Sentence configuration uses max 128 tokens; measure paraphrase/cross-language retrieval and quantization behavior rather than infer quality from its size. |

Sources: [E5 card](https://huggingface.co/intfloat/multilingual-e5-small), [MiniLM card](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2), [ONNX quantization guidance](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html). Repo metadata, file lists and small config/card files were queried on the review date; no weight/tokenizer downloads or model execution occurred.

Exact immutable revisions, selected model/tokenizer/config paths, sizes, URLs and SHA-256 values: [model manifest](evidence/t186-model-candidates-2026-11-11.json). Large-file digests are upstream LFS metadata, not locally verified artifact hashes. Read the actual artifact bytes and verify hashes before execution. Inspect model input/output shapes and tokenization/pooling behavior against pinned configuration; do not assume an ONNX output is already a sentence embedding.

## Approved experiment runtime

ONNX Runtime CPU plus tokenizers and NumPy, avoiding a PyTorch installation for this initial comparison. Exact direct candidates: onnxruntime 1.31.1, tokenizers 0.23.3, numpy 2.5.4. [Runtime manifest](evidence/t186-runtime-candidates-2026-11-11.json) pins 20 distributions including their active dependency metadata, filenames, URLs, registry SHA-256 values and license metadata. Python requirement specifiers were checked for 3.13.5. Wheel selection is metadata-based; native loadability, exact pip compatibility tags, licenses/notices and security findings remain preflight work. No package is declared safe or production-approved.

Total manifest download sizes: model/tokenizer/config files 615,349,351 bytes, runtime wheels 47,959,325 bytes (about 663 MB combined). Download size is not installed footprint or peak RAM. Do not let a resolver install unlisted packages or build from source. Extras, GPU runtimes and remote model code are excluded. Fetch exact listed files, verify registry/LFS identities and report any missing prerequisite before adding it.

## Diagnostic fixture and keyword reference

- [Fixture v1](../../tests/fixtures/t186_retrieval_v1.json): 12 invented memories, 36 labeled positive queries (12 lexical, 12 cross-language, 12 paraphrase including informal Spanish), one foreign-owner distractor and one global record. It contains no real user memory.
- [FTS5 harness](../../scripts/benchmark_keyword_retrieval.py): Unicode tokenization, quoted OR terms, BM25 top-5, SQL owner predicate before returning records. This is a standalone benchmark, not an application memory backend or proof of RBAC. Corpus-wide BM25 statistics still include fixture distractors.
- Command: `.venv/Scripts/python.exe scripts/benchmark_keyword_retrieval.py tests/fixtures/t186_retrieval_v1.json`.
- [Host result](evidence/t186-keyword-host-2026-11-11.json): 36 queries, lexical Recall@5 1.0, cross-language 0.0, paraphrase 0.5; overall Recall@5 0.5, MRR@5 0.4431. Fixture SHA-256 is embedded in that result. Host p95 query latency about 0.0564 ms on the tiny in-memory corpus; it is not a VM speed claim.
- No translation/stemming/tuned query expansion; results describe this reference only, not the best possible keyword implementation.

## D4 approved isolated experiment

Approve downloading and installing only artifacts in the two manifests, on a new isolated copy of the existing Debian ARM64 VM with CPython 3.13.5/glibc 2.41 or a separately confirmed compatible runtime. Generate synthetic databases/indexes only; never load actual user memory. Copy the original disk/UEFI assets, verify guest health/host key and use private loopback SSH. No service, production database, encrypted memory backend, credentials or package-policy bypass changes.

Given the approved artifacts, when running the experiment, then verify hashes, compatible native dependencies, CPU provider, declared licenses and model/config identity before inference; refuse mismatches. Disable inference-time downloads, remote code and runtime telemetry where supported; run offline and record any unsupported control. Loading model files does not authorize arbitrary code. Runtime evaluation must stop if unapproved prerequisites are required.

Run MiniLM ARM64 qint8 first and E5 FP32 second, unloading one before loading the other. Use one CPU inference thread initially and serialize heavy work. Approved experiment ceilings: 2 GiB peak process RSS, 4 GiB additional lab disk usage, and 30 minutes per model run under TCG; report ceilings reached as unavailable/failed measurements, never change them silently. These are experiment limits, not accepted production resource policy.

Compare both models and FTS5 on identical authorized candidate sets. Record Recall@5 and MRR@5 by category, cold load, warm query p50/p95, indexing throughput, RSS/disk, input truncation, model/revision, runtime identity and queue time separately. Approved diagnostic gates: lexical Recall@5 1.0; cross-language and paraphrase Recall@5 at least 0.8 each, overall MRR@5 at least 0.75; warm end-to-end query p95 at most 2 seconds over a deterministic 1,000-record synthetic corpus after ten warmup queries and at least 100 timed queries. Freeze expansion recipe and expected labels before measuring; do not duplicate target answers as synthetic distractors. Evaluate 10,000-record scale separately rather than extrapolate. Thresholds guide the experiment; they are not release acceptance from a 36-query set.

Before release, T237 must extend/freeze held-out no-match, ambiguity, stale/conflicting memory, long/chunk-boundary, poison text and cross-user/guest cases, including agreement labels and confidence/abstention evaluation. Do not interpret top-k similarity as proof that a memory answers a question. Freeze fixture hashes and thresholds before comparing results; revised fixtures require separate versioned results.

Given unsuitable quality/performance, when comparing results, then retain measured keyword fallback and report the semantic gap without claiming bilingual parity. No production model selection is approved by passing this experiment. Embedding cache/index persistence must follow memory encryption/deletion rules and prevent cross-user retrieval; the experiment stores synthetic vectors only.

## Production routing boundary

The constitution delegates model-provider access through omniroute. This standalone local benchmark is not a proposal to add a direct production model path. Q-26 leaves production embedding location open. Verify an omniroute embedding API and compatible local serving contract under T227/T228 before selecting it; no embedding endpoint is assumed to exist. Any production architecture exception requires an explicit proposal and applicable owner authorization. Real memory must not be sent to a new external embedding provider under D4.

Owner response: Approved on 2026-11-11 ("si, apruebo D4") only for the exact isolated comparison and its stated limits; changes to manifests/versions require review. This does not waive T225/T183/T237 or close T186.

## Validation evidence

Host keyword benchmark exit 0; fixture IDs/relevance references and scoped returns asserted by the harness. Metadata dependency closure and Python requirement checks passed; no native/model compatibility claim. `git diff --check`, Python syntax and new local documentation links/whitespace checked. No application runtime code, dependencies, migrations, production policies or constitution changed; no Django suite or VM/model run performed for this preparation.

## D4 execution record - 2026-11-11

Status: Experiment ended. MiniLM completed; E5 incomplete with unverified termination cause. Owner approved the exact D4 manifests in this session. No production model selection is implied.

- Prepared a new temporary copy of the existing disk and writable UEFI variables, leaving original assets untouched. Inactive copied disk passed qemu-img check. Guest: Debian 13.7, aarch64, Python 3.13.5, glibc 2.41, four Cortex-A76 vCPUs, about 8 GiB RAM, QEMU TCG. Guest systemd reported running and no failed units.
- Host verified all 34 selected artifact hashes and lengths (663,308,676 bytes); guest independently verified all 34 hashes. An initial verification used Windows path separators and failed before installation; normalized manifest paths for Linux and reran successfully. Exact guest wheel tags were confirmed against packaging.tags.sys_tags.
- Installed only the 20 listed wheels with `venv/bin/python -m pip --isolated install --no-index --no-deps --no-compile artifacts/wheels/*.whl`. pip check returned no broken requirements. No source build, additional runtime package, service or production database changes.
- [Wheel ELF/license inspection](evidence/t186-wheel-preflight-2026-11-11.json): 28 ELF native objects, all AArch64. Actual isolated inference imports establish loadability for exercised components only. [Direct-dependency OSV lookup](evidence/t186-direct-dependency-osv-2026-11-11.json) returned empty responses for the three direct versions, not a proof of safety. No separate transitive audits claimed.
- Tokenizers wheel lacks a license file; [tagged upstream license follow-up](evidence/t186-license-followup-2026-11-11.json) verified Apache-2.0 at v0.23.3. Model cards declare MIT for E5 and Apache-2.0 for MiniLM; complete notices for redistribution remain a release follow-up.
- [Frozen scale fixture](../../tests/fixtures/t186_retrieval_scale1000_v1.json): 1,000 records, SHA-256 `8bf6f901f49dcebd8542ac3419b6a344baa308e8451ead23edc198063982c2e2`. It adds 986 deterministic inventory-record distractors to fixture v1 without duplicating target answers; labels unchanged. This is an easy diagnostic distractor distribution, not a realistic memory corpus or held-out release test.
- [Semantic harness](../../scripts/benchmark_semantic_retrieval.py) uses CPU only, one inference thread, masked mean pooling with normalized vectors, model-specific query/passage prefixes and max lengths. Indexes one record per call; ten warmup queries and 108 timed queries. Authorization fixture filtering precedes similarity ranking; this does not establish application RBAC. Queue wait is zero for this isolated direct launch.
- Inference launcher: `sudo -n unshare --net -- setpriv --reuid=1001 --regid=1001 --init-groups timeout --signal=TERM --kill-after=5 1800 /tmp/superharry-t186-d4/venv/bin/python benchmark_semantic_retrieval.py ...`. Process verifies its route table is empty and effective UID is non-root. No firewall/service settings changed. ONNX telemetry disabled after module import; initialization emitted an in-memory device-ID warning before disable, inside the network-isolated namespace. No route to an external service exists in the inference namespace.
- Guest lab footprint after install was about 790 MiB, below its 4 GiB ceiling. Harness monitors peak RSS against 2 GiB; external timeout enforces the 30-minute per-run bound. GPU/remote model code are not used. No test failure or incomplete metric is promoted to acceptance.

### Completed MiniLM measurement

- [Raw result](evidence/t186-minilm-vm-2026-11-11.json): process exit 0; all five diagnostic gates passed. Corpus 1,000 records, 36 unique labeled queries, ten warmups and 108 timed queries. Recall@5 = 1.0 in each category; overall MRR@5 = 0.92685 (lexical 1.0, cross-language 0.93333, paraphrase 0.84722).
- Warm query p50 0.35467 s, p95 0.49159 s; index 925.4016 s, 1.08061 records/s; session construction 5.9033 s; total process 981.681 s. Peak RSS 486,820 KiB; normalized vector matrix 1,536,000 bytes; zero input truncations. Session construction time excludes Python module import and first fixture preprocessing.
- [Matched guest FTS5 reference](evidence/t186-keyword-vm-2026-11-11.json): same corpus/labels, ten warmups and 108 timings; overall Recall@5 0.5/MRR@5 0.44306, cross-language Recall@5 0; p95 28.4387 ms. The semantic gain has a measured latency/indexing cost; this does not establish superiority over every keyword design.
- [Guest profile](evidence/t186-vm-profile-2026-11-11.json) records kernel/runtime, fixture and harness identities. All figures are TCG guest observations; no native hardware or production-load inference.
- MiniLM process ended before E5 launch; no simultaneous heavy model execution. E5 ended incomplete as recorded below.

### E5 incomplete measurement and final disposition

- [Raw partial report](evidence/t186-e5-vm-partial-2026-11-11.json): last durable checkpoint confirms 150 indexed records at 1,141.248 seconds, peak RSS 903,408 KiB, session construction 5.3469 seconds. These are checkpoint observations, not final throughput or total-duration measurements; work between that checkpoint and termination is not counted as verified progress.
- The SSH/launcher session ended with exit 1 at approximately the configured 30-minute window. It did not return the expected timeout code 124, and the diagnostic log contains the initialization telemetry warning without a Python traceback. A subsequent 0.2-second timeout probe through the same sudo/unshare/setpriv wrapper returned 124 correctly. The exact cause of the model-run termination remains unverified; do not report a verified timeout or successful E5 benchmark.
- Confirmed no inference process remained after termination. Guest systemd still reported running with no failed units; requested normal poweroff. No automatic model retry or extension of the resource limits occurred.
- E5 never reached query measurement in the saved report. Recall, MRR, warm latency and complete indexing throughput are unavailable; no quality comparison against MiniLM is claimed. The observed partial indexing cost does not justify extending the approved experiment silently.
- Recommendation for further T237 validation: continue with the measured MiniLM ARM64 qint8 candidate. It passed this small synthetic diagnostic, while E5 did not produce a complete result under this experiment. This is not production adoption or release acceptance.
- Remaining: held-out/no-match/ambiguity and adversarial fixtures, realistic memory distributions and 10,000-record scale, memory schema and per-user encrypted index/cache design, deletion semantics, gateway embedding contract/location, resource scheduling and integrated application tests. T186 remains open with T183/T237 prerequisites; T225 remains a prerequisite of T237.
- Evidence and scope updated in owner-attention/backlog/task review. Constitution unchanged; no new policies, application dependencies or production configuration activated. Tests apply to standalone benchmark code, not the Django application suite.

### Final verification and retained lab

QEMU exited 0 after normal guest poweroff. Offline lab retained at `C:/Users/Matias/AppData/Local/Temp/superharry-t186-20261111-174414`, with tracking file `C:/Users/Matias/AppData/Local/Temp/superharry-t186-active.txt`; original VM disk/UEFI assets were not writable test targets. Host logical lab size measured 3,318,192,684 bytes, below 4 GiB; guest lab about 791 MiB. No model process remains running.

Final checks passed: standalone Python syntax; 108-timing/36-label keyword smoke check; artifact/result/fixture/harness identity consistency; affected local links and whitespace including untracked records; 65 unique open backlog IDs match 65 unique queue IDs; unchanged constitution SHA-256; project progress exit 0 (10/75 markers, T225 first open); git diff --check. No application or migration changes, Django suite, production activation or release acceptance claimed.

Selection synchronization checks (2026-11-11): selected revision/artifact digest match the D4 manifest; affected owner/review links and whitespace pass; project progress exit 0; git diff --check passes; constitution SHA-256 unchanged. Documentation-only owner decision; no new model run or installation.
