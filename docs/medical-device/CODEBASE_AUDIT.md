# Codebase Audit and Readiness Rating

## Audit conclusion

The repository is materially stronger as research and controlled-development software, but it is
**not ready for medical use**. The software release gate is deliberately blocked. No engineering
review can establish zero error probability, and no amount of code can replace clinical evidence,
human-factors validation, an operating quality system, site qualification, or regulatory
authorization.

This is a risk-based engineering assessment of the repository state on 2026-07-16, not an
independent verification report, clinical validation, conformity assessment, or regulatory
certificate. Ratings use 10 as “credible release evidence exists for the stated scope,” not simply
“the code looks good.”

## Ratings

| Domain | Rating | Current assessment | Release requirement |
|---|---:|---|---|
| Segmentation/postprocessing correctness | 8/10 engineering, unscored clinically | Disconnected foreground retention is fixed and regression-tested; inputs and geometry fail closed. | Independent reference-oracle verification and locked analytical/clinical datasets. |
| Metric correctness | 8/10 | Classic AJI and AJI+ are distinct; PQ uses strict `IoU > 0.5`; brute-force cases cover matching semantics. Historical results are explicitly relabeled/corrected. | Re-run the full frozen baseline and independently reproduce the statistical report. |
| Checkpoint/model integrity | 8/10 | Distinct versioned training/inference contracts, weights-only deserialization, strict state loading, byte-level SHA-256 verification, digest-keyed cache and controlled-mode approved hash. Legacy unsafe training resumes are rejected. | Approved model-development record, dataset lineage, locked model report and signed artifact. |
| Input and API safety | 8/10 | Complete request bodies are bounded before multipart parsing for declared or streamed delivery; declared/decoded format, single-frame, file-byte/pixel, safe-identifier and locked-override controls fail closed. | Independent multipart/image fuzzing, concurrent resource-exhaustion testing, gateway integration and API verification. |
| Authentication/authorization boundary | 7/10 | Constant-time service-token validation and trusted actor identity are enforced in controlled mode; browser token exposure is prohibited by topology. | Qualified OIDC/RBAC gateway, key rotation, site policy tests and penetration testing. |
| Audit/provenance | 8/10 | Input/model hashes, release/settings/device provenance and durable sequenced/hash-chained records with process locking, persisted-head truncation detection, and readiness checks. | Qualified durable/WORM retention, backup/restore, external head anchoring, multi-system reconciliation and audit review SOP. |
| Output semantics and reports | 8/10 | “Foreground score” and “TTA disagreement” replace diagnostic probability/uncertainty claims; no-TTA omits disagreement; reports carry provenance and disclaimers. | Summative comprehension/usability validation and regulator-approved labeling. |
| Architecture/maintainability | 8/10 | Analysis orchestration, postprocessing, validation, runtime and provenance have focused modules; API is a boundary layer; no generated dead-code paths were added. | Independent design review, long-term ownership and controlled anomaly/change process. |
| Automated verification | 7/10 | 102 tests pass; Ruff, mypy, shell, medical-evidence validation, TypeScript and production build pass; aggregate coverage is 83.79% against an enforced 80% gate. Tiled inference is 94% covered with border/seam invariants. | Independent property/fuzz/end-to-end/soak/fault-injection evidence; training orchestration remains below desired safety-critical depth. |
| Dependency/supply chain | 8/10 | Hash-locked runtime, CPU-only Linux Torch source, immutable CI/base-image/scanner pins, non-root image, Python SBOM/hash receipt, and configured CodeQL plus Trivy image/configuration/secret gates with retained container CycloneDX; Python/npm audits report zero known vulnerabilities at audit time. | Execute and independently review frozen-commit SAST/container evidence; SBOM signing, license scan, supplier qualification, recurring monitoring and vulnerability disposition. |
| Deployment/operations | 5/10 | Reproducible CPU image, health/readiness split, load harness, locked settings and documented gateway/read-only topology. | Production infrastructure, GPU image if used, IQ/OQ/PQ, capacity/soak, monitoring, backup/rollback and disaster exercises per site. |
| Clinical evidence | 1/10 | A study framework exists; no repository evidence establishes clinical performance or utility. | Independent multi-site retrospective and prospective studies under approved protocols, plus reader/utility study if claimed. |
| Usability/human factors | 1/10 | Safer terminology and workflow constraints are implemented; no representative-user validation exists. | Formative and summative studies with oncologists/pathologists/laboratory staff. |
| QMS/regulatory/privacy/postmarket | 2/10 | Controlled draft manuals, procedures, protocols, registers, a document index and fail-closed evidence checks exist; accountable owners, operating records, approvals and authorizations do not. | Operational QMS, market strategy/authorization, privacy agreements/DPIA, labeling, complaints/vigilance/CAPA readiness. |

**Overall research/development software readiness: 8/10.**
**Overall medical deployment readiness: 2/10 and release blocked.** The latter cannot increase from
repository work alone.

## Critical findings remediated

1. **Silent foreground loss in watershed.** A disconnected retained component without a qualifying
   peak could disappear whenever another component had a peak. Every retained component now receives
   a marker, and the regression test verifies that every foreground pixel obtains an instance label.
2. **Metric mislabeling and boundary mismatch.** The previous “AJI” calculation was one-to-one AJI+
   and PQ accepted `IoU == 0.5`. Classic AJI/AJI+ are now separate and PQ uses the published strict
   threshold. Historical evidence carries a correction notice and requires rerun.
3. **Unverified checkpoint loading.** Controlled operation now binds loading to the approved SHA-256
   and loads the exact verified bytes under a versioned model contract.
4. **Permissive uploads.** Filename/type claims alone are no longer trusted; complete declared or
   streamed request bodies are bounded before multipart parsing, and decoded format, frame count,
   file/pixel limits and RGB shape are validated before inference.
5. **False confidence semantics.** TTA variation is no longer called calibrated uncertainty, a
   no-TTA run no longer fabricates a zero uncertainty map, and foreground output is labeled a score.
6. **Missing clinical audit trail.** Analyses now include canonical provenance and controlled-mode
   durable hash-chained audit records; unavailable or corrupt audit storage blocks readiness.
7. **Uncontrolled runtime settings.** Controlled mode requires a release ID, checkpoint digest,
   audit store and service token and refuses per-request model/postprocessing overrides.
8. **Release by convention.** A machine-readable manifest and release command now require all 13
   gates, assigned owners, dated approvers, repository-contained evidence, explicit approved
   disposition, exact checkpoint and intact audit storage.
9. **Supply-chain drift.** Runtime dependencies are hash locked, training-only packages are excluded
   from the inference image, CI actions/base images are immutable pins, and Linux resolves official
   CPU Torch rather than CUDA packages.
10. **Oversized boundary modules.** Analysis/report orchestration and postprocessing were extracted
    from the API/predictor into focused modules with explicit contracts and tests.
11. **Unsafe training-checkpoint deserialization.** Training RNG state now uses a weights-only-safe
    tensor/primitives schema (format version 3); legacy unrestricted-pickle resume artifacts fail
    closed. Checkpoint writes use atomic file and directory synchronization. Inference remains on its
    distinct version-2 weights-only schema.

## Residual high-risk work

- Freeze intended use, supported tissue/stain/scanner/specimen/input envelope, claims and human-review
  responsibility. Current ambiguity makes clinical risk and validation scope impossible to close.
- Resolve dataset/model/commercial licensing and prove patient/site-level data provenance,
  representativeness, independence and privacy compliance.
- Reproduce all corrected metrics on a frozen candidate; establish clinically justified acceptance
  limits, confidence intervals, subgroup/worst-case performance and failure-detection behavior.
- Complete independent multi-site and prospective clinical validation. PanNuke benchmark results do
  not establish performance in an oncology laboratory.
- Validate the complete user workflow and labeling with representative trained and untrained users,
  including failure, out-of-distribution, unavailable and override states.
- Perform independent threat modeling, fuzzing, penetration, container/IaC/SBOM/license scanning,
  denial-of-service, concurrency, soak, recovery and backup/rollback verification.
- Qualify the exact production hardware/software image at every site. The verified repository image
  is CPU-only; any GPU/driver build is a different controlled artifact requiring regression evidence.
- Operate QMS, privacy, complaint, vigilance, CAPA, postmarket, change-control and regulator processes
  with competent human owners and retained approvals.

## Verification evidence from this audit

- Repository verification components: 102 tests pass; Ruff, mypy over 37 source files, shell and
  medical-evidence validation, TypeScript
  typecheck and the production UI build pass.
- Coverage: 83.79% against an enforced 80% aggregate CI threshold; tiled inference is 94%, audit
  provenance 93%, request limiting 94%, runtime configuration 97%, and image validation 92%.
- Python dependency audit: no known vulnerabilities found; the local project itself is not a PyPI
  package and is reviewed as source.
- Locked runtime SBOM: CycloneDX 1.4, 51 components, zero vulnerabilities, with requirements and
  SBOM SHA-256 receipt; this developer artifact must be regenerated for the frozen release.
- npm audit: zero vulnerabilities reported.
- Lock regeneration: `uv.lock` is current and `requirements.lock` reproduces exactly.
- Container security: a checksum-verified Trivy 0.70.0 developer scan rejected both the prior
  Debian 13 slim runtime (22 high/critical OS findings) and a Debian 12 slim replacement (23
  high/critical OS findings). No finding was suppressed. The Dockerfile now uses an
  immutable-digest distroless Debian 12 Python runtime, separated the dependency build stage, had no
  runtime shell or package manager, and ran as UID/GID 65532. Python 3.11 was added to the full CI
  test matrix. The local ARM64 dependency build completed,
  but local Docker storage failed with filesystem I/O errors during final image commit. GitHub CI
  subsequently built the AMD64 image and passed its read-only, native-library, audit-chain and
  numeric non-root smoke checks. Its Trivy gate correctly rejected the image because the pinned
  distroless Debian runtime still contains release-blocking OS findings, including critical SQLite
  and zlib findings. No finding is suppressed and no passing final-image security claim is made.
  The current candidate replaces that runtime with an immutable Wolfi base, exact Python 3.12
  package version, numeric non-root user, and no runtime package manager or shell. Its native ARM
  image passed read-only/native-library/audit/CPU smoke checks and Trivy 0.70.0 reported zero
  high/critical Wolfi or Python findings; the repository configuration/secret scan was also clean
  and a valid container CycloneDX SBOM was generated. Clean native AMD64 GitHub quality run
  [`29517452489`](https://github.com/VampFay/sem6-miniPwith-withdaBOIS-/actions/runs/29517452489)
  reproduced the build and smoke checks, passed the high/critical image gate and repository
  configuration/secret scan, and retained the container SBOM for commit
  `bd69363b10373d6d1a627e4cc3a6c0bc386e2498`. The identified base-image finding is therefore closed
  for this repository-controlled candidate at that point in time, without suppressions. Independent
  frozen-release scan review, signed-image provenance, penetration/DAST/fuzz testing, infrastructure
  scanning and recurring vulnerability disposition are still required before the `SOFTWARE` or
  `DEPLOYMENT` gate can be approved.
- `./setup.sh release-gate`: exits nonzero and lists all 13 pending gates, which is the correct current
  safety outcome.

These results are developer verification evidence only. Independent execution against a frozen
commit, signed image and approved checkpoint is required for the `SOFTWARE` gate.
