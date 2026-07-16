# Safety-Classified Software Requirements

These requirements are implementation baselines, not a complete IEC 62304 classification. The
manufacturer must assign software safety class after the clinical harm analysis is approved.

| ID | Requirement | Verification |
| --- | --- | --- |
| SWR-001 | Every decoded foreground pixel retained for watershed shall receive a nonzero instance label. | Regression test with disconnected low-peak component. |
| SWR-002 | AJI, AJI+, and PQ definitions shall be distinct; PQ matching shall use strict IoU > 0.5. | Analytical unit tests and brute-force references. |
| SWR-003 | The service shall accept only single-frame JPEG, PNG, or TIFF whose declared and decoded formats agree. | Adversarial decoder tests. |
| SWR-004 | The complete analysis request shall be byte-bounded before multipart parsing, including when Content-Length is absent, and file-byte and decoded-pixel limits shall be enforced before inference. | Declared-length, streamed-body, API-file, and decoder boundary tests. |
| SWR-005 | Controlled mode shall require a non-development release ID, approved model SHA-256, audit directory, high-entropy service credential, and at least one exact HTTPS browser origin. | Runtime configuration tests. |
| SWR-006 | The exact checkpoint bytes loaded shall match the configured approved SHA-256. | Digest mismatch and mutation tests. |
| SWR-007 | Controlled operation shall reject unauthenticated requests, missing actor identity, and all client inference-setting overrides. | API authorization tests. |
| SWR-008 | Each analysis shall record input/model/software/settings/time/device provenance without recording source pixels in the audit event. | API/report/provenance tests. |
| SWR-009 | Controlled audit records shall be durable, monotonically sequenced, hash chained, process serialized, anchored by a persisted head, and verified before append. Record edits, sequence gaps, chain forks, and suffix truncation shall block operation. | Chain, truncation, and multiprocess tests plus site filesystem qualification. |
| SWR-010 | A no-TTA run shall not expose a zero map as uncertainty; TTA variation shall be labeled disagreement, not calibrated uncertainty. | API schema and UI build verification. |
| SWR-011 | Reports shall state that output is not cleared for diagnosis and include complete hashes in a provenance section and JSON sidecar. | PDF/content and API contract tests. |
| SWR-012 | The release command shall fail unless every required human/evidence gate is approved and controlled runtime verification passes. | Release-gate unit and negative acceptance tests. |
| SWR-013 | The service shall emit no-store and browser hardening headers for API responses. | API header tests. |
| SWR-014 | Runtime dependencies shall have zero known unresolved critical/high vulnerabilities at release, with deviations formally risk accepted. | Independent SBOM and vulnerability scan record. |
| SWR-015 | A CycloneDX runtime SBOM shall be generated from the hash-locked requirements, and a receipt shall bind the requirements and SBOM hashes, component/vulnerability counts, generator, time, and audit disposition. A failed audit shall block release. | SBOM-generation unit tests and CI artifact validation. |
| SWR-016 | Training and inference checkpoints shall load through restricted weights-only deserialization under distinct versioned schemas. Checkpoint creation shall use atomic durable replacement. Legacy training checkpoints requiring unrestricted pickle deserialization shall be rejected. | Safe-schema serialization, atomic-write, resume, and legacy-rejection tests. |
| SWR-017 | CI shall run immutable-pinned CodeQL analysis for Python and JavaScript/TypeScript; scan the built container for high/critical OS and library vulnerabilities; scan repository configuration and secrets; and retain a container CycloneDX SBOM. Findings at the configured release-blocking severity shall fail CI. | Workflow schema/pin review and independently retained CI/SARIF/SBOM records. |

Nonfunctional requirements still requiring quantified acceptance values include maximum validated
image size, latency/throughput, availability, recovery time/objective, audit retention, concurrent
load, scanner/color acceptance, browser/display support, and site network constraints. Those values
must be derived from intended use and risk analysis, not guessed by developers.
