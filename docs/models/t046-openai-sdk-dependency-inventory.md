# T046: OpenAI SDK dependency review inventory

Status: evidence inventory for review, 2026-11-04; **not approved for installation, redistribution or release**. This document does not authorize changes to dependencies or perform live OpenAI requests. The owner supplied a local API credential for integration; no credential was read or included in this inventory.

## Scope and method

The current Windows Python 3.12 environment reports `openai==3.45.0`, but the repository `requirements.txt` declares only Django. The list below starts with the installed OpenAI version and follows PyPI version-specific dependency metadata under a **hypothetical** CPython 3.13.5, Linux `aarch64`, no-extra environment; those markers and the exact versions are not a target-guest resolver run or a lockfile. The candidate versions come from the local Windows environment; this does not establish how they were installed or prove they are an approved compatible Linux closure. No application packages, binaries or source distributions were downloaded or installed for this inventory.

PyPI JSON metadata was fetched from its versioned project endpoints on 2026-11-04. For each candidate the selected filename is either a universal wheel or a CPython 3.13 manylinux_2_17/aarch64 wheel, and the SHA-256 is the value **reported by PyPI**. The corresponding artifacts were not downloaded, so their bytes have not been independently hashed, executed, signature-verified, or tied to a trusted build. PyPI registry presence and hashes do not establish provenance, license clearance or absence of vulnerabilities. Compatibility depends on the actual guest interpreter, glibc/platform tags and native library closure; those are not verified here. All selected wheel records were marked non-yanked at lookup time.

## Candidate artifacts and declared licenses

| Distribution | Version | License declared in PyPI metadata | Candidate wheel | Registry-reported SHA-256 |
|---|---|---|---|---|
| [annotated-types](https://pypi.org/pypi/annotated-types/0.8.0/json) | 0.8.0 | MIT | `annotated_types-0.8.0-py3-none-any.whl` | `f072f4d804ea359e4eaf198b1af7a8b0943881a87f31bb764f8bf219bb9419e0` |
| [anyio](https://pypi.org/pypi/anyio/4.16.0/json) | 4.16.0 | MIT | `anyio-4.16.0-py3-none-any.whl` | `c66ae634e0b8228396b801741beb3294326d4b6102f7bba4041c0dfb58c29026` |
| [h11](https://pypi.org/pypi/h11/0.16.0/json) | 0.16.0 | MIT | `h11-0.16.0-py3-none-any.whl` | `63cf8bbe7522de3bf65932fda1d9c2772064ffb3dae62d55932da54b31cb6c86` |
| [httpcore2](https://pypi.org/pypi/httpcore2/2.16.0/json) | 2.16.0 | BSD-3-Clause | `httpcore2-2.16.0-py3-none-any.whl` | `5c4358319f2602d984ad93182c9fee5160f22e9da7babdda870a5e7c4e2dc34f` |
| [httpx2](https://pypi.org/pypi/httpx2/2.16.0/json) | 2.16.0 | BSD-3-Clause | `httpx2-2.16.0-py3-none-any.whl` | `fd2c5d7909e8d86fe92d53020c310ca0e4e431b838c207c5754b9bbf0308d49a` |
| [idna](https://pypi.org/pypi/idna/3.20/json) | 3.20 | BSD-3-Clause | `idna-3.20-py3-none-any.whl` | `ab7ae7122974553370f0bdb919e1a960b2cd1bc1ef0276416d896db81c14582c` |
| [jiter](https://pypi.org/pypi/jiter/0.18.0/json) | 0.18.0 | MIT | `jiter-0.18.0-cp313-cp313-manylinux_2_17_aarch64.manylinux2014_aarch64.whl` | `9623fc90f1a4754452a525383ce70476476c16556098944709b8cdbd9ad905f0` |
| [openai](https://pypi.org/pypi/openai/3.45.0/json) | 3.45.0 | Apache-2.0 | `openai-3.45.0-py3-none-any.whl` | `b63aa90e3b7b57b501f2bba231a17976618aa133f457562ad84a5c6431fd0425` |
| [pydantic](https://pypi.org/pypi/pydantic/2.14.2/json) | 2.14.2 | MIT | `pydantic-2.14.2-py3-none-any.whl` | `7efbf7507b937931cd32a5755acb00ea1cf5ccb1d4e8067a5850d5069e382118` |
| [pydantic-core](https://pypi.org/pypi/pydantic-core/2.50.2/json) | 2.50.2 | MIT | `pydantic_core-2.50.2-cp313-cp313-manylinux2014_aarch64.manylinux_2_17_aarch64.whl` | `f142cd663d1148ed32993ed9a58e5c67ea312f446a01a6c13a956945aafc9f23` |
| [sniffio](https://pypi.org/pypi/sniffio/1.3.1/json) | 1.3.1 | MIT OR Apache-2.0 | `sniffio-1.3.1-py3-none-any.whl` | `2f6da418d1f1e0fddd844478f41680e794e6051915791a034ff65e5f100525a2` |
| [truststore](https://pypi.org/pypi/truststore/0.10.5/json) | 0.10.5 | MIT | `truststore-0.10.5-py3-none-any.whl` | `9aaaedaefaf06d8b206278cf8b5012bc897f485a874503501e12d776df78951c` |
| [typing-extensions](https://pypi.org/pypi/typing-extensions/4.16.0/json) | 4.16.0 | PSF-2.0 | `typing_extensions-4.16.0-py3-none-any.whl` | `481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8` |
| [typing-inspection](https://pypi.org/pypi/typing-inspection/0.4.5/json) | 0.4.5 | MIT | `typing_inspection-0.4.5-py3-none-any.whl` | `bc210535442b39e1bf2805e0c7a17dfd6a4ace760c84c7f7d16245d23a6b1c39` |

## Metadata dependency edges (hypothetical guest markers)

- `anyio -> idna>=2.8`
- `anyio -> typing-extensions>=4.16.0`
- `httpcore2 -> h11>=0.16`
- `httpcore2 -> truststore>=0.10`
- `httpx2 -> anyio>=4.10`
- `httpx2 -> httpcore2==2.16.0`
- `httpx2 -> idna>=3.18`
- `httpx2 -> truststore>=0.10`
- `openai -> anyio<5,>=4.10.0`
- `openai -> httpx2<3,>=2.12.0`
- `openai -> jiter<1,>=0.16.0`
- `openai -> pydantic!=2.0.*,!=2.1.*,!=2.2.*,!=2.3.*,<3,>=1.10.13`
- `openai -> sniffio`
- `openai -> typing-extensions<5,>=4.14`
- `pydantic -> annotated-types>=0.6.0`
- `pydantic -> pydantic-core==2.50.2`
- `pydantic -> typing-extensions>=4.16.0`
- `pydantic -> typing-inspection>=0.4.4`
- `pydantic-core -> typing-extensions>=4.16.0`
- `typing-inspection -> typing-extensions>=4.15.0`

## Missing evidence and decisions

- The metadata-only traversal found no missing candidate versions, incompatible declared version ranges, active extras, or Python-version mismatches for the hypothetical target. This is not an independent package resolver or proof of a complete build/runtime closure.
- Select and approve exact tool versions, indexes, interpreter and target guest configuration; run a reproducible target-environment resolver for the combined Django and OpenAI dependency graph, including build dependencies and platform markers. Do not assume the current Windows installation is representative of Linux ARM64.
- Obtain and independently verify exact artifacts against trusted publisher provenance/signatures or attestations where available. A registry-reported digest, local version and wheel tag alone are not sufficient. Inspect native-wheel dependencies and ARM64 compatibility on the actual guest.
- Review each package and transitive dependency against current advisory/malware evidence, including incomplete/unavailable checks; define advisory-data freshness and blockers under the accepted package/dependency process. No vulnerability scan or malicious-package clearance was performed.
- Inspect actual license files, bundled components and redistribution notices; the table reports SPDX expressions or license text declared by registry metadata only. The `sniffio` expression is `MIT OR Apache-2.0`; no license branch was chosen or cleared here.
- Prepare and approve a pinned, hash-verified lock/artifact procedure and documented rollback; inspect SDK transport defaults (timeouts, retries and cancellation), privacy/logging, the actual target service's TLS trust and account configuration before any deployment. Do not place credentials in manifests, outputs or shared evidence.
- The real-provider application integration still needs protected-context delivery, budget enforcement, cancellation/error/usage handling, role boundaries, local fallback and target acceptance. This inventory does not close T043/T044/T046/T048/T049.

Evidence: current `constitution.md` SHA-256 `E18BEBC0672327542C364FFD7613DFD94A5F3AB206EC0ADA1895F67213C38F7C`; local installed-distribution metadata and the PyPI JSON endpoints linked above. No runtime package or system installation, provider request, secret access, VM execution or target acceptance was performed.
