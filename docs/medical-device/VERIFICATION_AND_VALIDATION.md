# Verification and Validation Plan

## Software verification

Each requirement and risk control requires objective evidence at the lowest practical level:
static analysis and review; unit/property tests; API contract and negative tests; model artifact
compatibility; end-to-end report/provenance tests; dependency/SBOM scanning; container and
infrastructure scanning; fuzzing of image and multipart boundaries; concurrency, soak, resource
exhaustion and recovery tests; and site installation qualification. Safety-critical verification
must be reviewed by someone independent of its implementation.

Multipart verification includes oversized declared lengths, absent lengths with chunked delivery,
ambiguous/invalid lengths, exact-boundary bodies, malformed encodings, interrupted streams, and
concurrent requests at the qualified gateway/application limits. Tiled inference verification
includes non-divisible dimensions, final-border coverage, overlap seams, constant-map invariants,
TTA inversion, padding, and full-image equivalence where an oracle is available.

Release evidence must record source commit, signed build identity, dependency lock/SBOM, container
digest, checkpoint digest, dataset versions, operating system/hardware, exact command, complete
logs, deviations, reviewer, and approval date. A passing developer workstation run is not release
verification.

The Python SBOM evidence consists of both the CycloneDX document and its generated receipt. The
independent reviewer shall recompute the requirements and SBOM hashes, confirm the component count,
verify a zero-vulnerability audit or approved deviation, and reconcile the SBOM with the container
inventory. Audit-storage verification shall include edit, middle-record deletion, suffix truncation,
sequence gap, concurrent writer, unavailable mount, backup/restore, and external-head reconciliation.
The frozen CI run shall additionally retain both CodeQL language analyses, Trivy image and
configuration/secret scan logs, and the generated container CycloneDX artifact. Every alert requires
documented triage; absence of a CI execution record is not equivalent to a passing scan.
Container verification shall run the complete Python suite on both Python 3.11 (production runtime)
and Python 3.12, build for the target architecture, verify the configured numeric non-root identity,
import the API plus native Torch/imaging stack under a read-only filesystem, append and verify an
audit record on the qualified writable mount, and reject any release-blocking Trivy finding.

## Model verification

Freeze the model, preprocessing, postprocessing, image acceptance rules, and operating point before
final validation. Re-run corrected AJI/AJI+/PQ metrics. Report detection/segmentation errors,
confidence intervals, per-site/scanner/stain/tissue/tumor/subgroup performance, worst-case strata,
empty/low-cell cases, artifacts, out-of-distribution inputs, repeatability, and inter-reader
comparisons. Thresholds and exclusions are selected only on development data.

## Clinical validation boundary

Clinical validation requires representative, legally usable, independently curated multi-site data
and a preregistered statistical analysis plan. Patient-level/site-level separation is mandatory.
The pivotal set is locked and accessed only after protocol and acceptance criteria approval.
Prospective silent-mode and workflow studies follow retrospective external validation. Any claim
that output changes diagnosis or care requires an appropriately powered clinical performance or
utility study and regulator/ethics input.

## Exit criteria

All required release-manifest gates approved; no unexplained test failures; all high risks reduced
and accepted; no unresolved critical/high security vulnerabilities unless formally justified;
clinical and usability acceptance criteria met; installation/rollback/backup restored at each
site; labeling matches evidence; and the regulator/quality authority authorizes release.
