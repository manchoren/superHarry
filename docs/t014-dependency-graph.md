# T014 partial dependency graph

Status: research evidence only, 2026-10-31. This graph is assembled from retained records; it is not a resolver result, lockfile, approved manifest, or package recommendation. No dependency was selected, installed, resolved, or executed.

## Exact npm artifact edges

The graph below records dependency and peer ranges from the exact npm package metadata inspected in [the artifact review](evidence/t014-authorized-npm-artifact-review.json). These four packages were authorized for research only. `@noble/hashes` is included because it is the recorded exact direct dependency of `otpauth`.

```mermaid
flowchart LR
    argon2["argon2 0.45.1"]
    phc["@phc/format"]
    crossenv["cross-env"]
    addonapi["node-addon-api"]
    nodebuild["node-gyp-build"]
    otpauth["otpauth 9.5.2"]
    noble["@noble/hashes 2.4.0"]
    markdown["react-markdown 10.1.0"]
    hasttypes["@types/hast"]
    mdasttypes["@types/mdast"]
    devlop["devlop"]
    hastjsx["hast-util-to-jsx-runtime"]
    urlattrs["html-url-attributes"]
    mdasttohast["mdast-util-to-hast"]
    remarkparse["remark-parse"]
    remarkrehype["remark-rehype"]
    unified["unified"]
    visit["unist-util-visit"]
    vfile["vfile"]
    typereact["@types/react peer"]
    reactpeer["react peer"]
    filetype["file-type 22.3.0"]
    inflate["@tokenizer/inflate"]
    strtok3["strtok3"]
    tokentypes["token-types"]
    uint8extra["uint8array-extras"]

    argon2 -->|"^1.0.0"| phc
    argon2 -->|"^10.1.0"| crossenv
    argon2 -->|"^8.9.0"| addonapi
    argon2 -->|"^4.8.4"| nodebuild
    otpauth -->|"2.4.0"| noble
    markdown -->|"^3.0.0"| hasttypes
    markdown -->|"^4.0.0"| mdasttypes
    markdown -->|"^1.0.0"| devlop
    markdown -->|"^2.0.0"| hastjsx
    markdown -->|"^3.0.0"| urlattrs
    markdown -->|"^13.0.0"| mdasttohast
    markdown -->|"^11.0.0"| remarkparse
    markdown -->|"^11.0.0"| remarkrehype
    markdown -->|"^11.0.0"| unified
    markdown -->|"^5.0.0"| visit
    markdown -->|"^6.0.0"| vfile
    markdown -.->|"peer >=18"| typereact
    markdown -.->|"peer >=18"| reactpeer
    filetype -->|"^0.6.0"| inflate
    filetype -->|"^10.6.3"| strtok3
    filetype -->|"^6.1.2"| tokentypes
    filetype -->|"^1.6.0"| uint8extra
```

This shows 20 declared dependency edges and two peer requirements, not their resolved versions. The peer nodes are requirements, not assertions that a compatible React or type package has been selected. Transitive, optional, platform-specific and build-tool closures for these edges remain unenumerated.

## Existing npm candidate metadata

On 2026-10-31, read-only requests to the official npm registry captured the declared package metadata for the 24 exact npm candidate roots already listed in T014 records. The reproducible [capture script](evidence/t014-transitive/capture_npm_candidate_edges.py) records only names, versions, declared dependency/optional/peer ranges, selected package constraints, publisher license labels, publisher integrity claims and raw-metadata digests. The [machine-readable edge evidence](evidence/t014-transitive/npm-candidate-edges.json) contains 115 required, five optional and 40 peer declarations (160 total), including 17 edges to another candidate root.

The root-to-root ranges are recorded but not evaluated against each other; no transitive versions were selected. The metadata and integrity claims come from the same registry and are not independent provenance. This adds direct range edges for the existing candidates, but does not close their transitive, build, bundled or platform-specific dependencies and is not resolver output.

## QEMU host package metadata traversal

The retained [QEMU inventory](evidence/t014-msys2/qemu-inventory.json) contains 159 package records and 502 dependency edges from an exploratory traversal rooted at `mingw-w64-ucrt-x86_64-qemu`. Its source database digest is `3253eb5ed9d16e936b4ca854d2ca2eb5c3d164322967f0dad21cf26eca484248`; [the inventory script](evidence/t014-msys2/build_inventory.py) records how edges were derived. The traversal matched 495 requirements by exact package name and seven through a unique declared `PROVIDES` name; four constrained edges received static version checks.

These are repository-metadata relationships, not a pacman transaction or solver-equivalent closure. Optional dependencies are recorded but are not traversed as required edges. The inventory does not establish trusted provenance, current advisory coverage, license dispositions, actual VM devices, or approval of any package.

## Boundary and next action

This is the graph available from existing retained evidence, not the complete T042/T014 dependency graph. Other candidate versions in the [T042 scope inventory](t014-t042-scope.md) do not have an artifact-backed dependency closure here. On 2026-10-31, the owner directed keeping the current work simple, not expanding research to additional unresolved roles, and creating separate tasks for concrete complications that arise later. This does not fill or waive those roles, change T042's hard prerequisites, or authorize a resolver. Keep missing edges explicit. T014 remains blocked until the applicable graph, checks, compatibility evidence and approvals are complete.
