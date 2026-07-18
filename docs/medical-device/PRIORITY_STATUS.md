# Medical Deployment Priority Status

**Status date:** 2026-07-18. **Overall disposition:** release blocked; research use only. “Implemented”
below means repository-controlled engineering or a draft protocol exists. It never means a study,
QMS approval, site qualification or regulatory authorization occurred.

## Ten-workstream execution layer

Implemented in the repository: `EXECUTION_WORKSTREAMS.json` now controls all ten workstreams from
legal-manufacturer/intended-use governance through daily professional use. Each workstream has an
execution plan, objective-record template, dependency graph and explicit exit criteria. CI rejects
missing workstreams/templates, invalid schemas, dependency cycles, false clinical authorization,
false readiness with unassigned accountability, and removal or downgrading of a critical daily-use
control. The controlled document index now covers 68 artifacts.

Open/blocking: all ten workstreams remain `execution_pending`; their owners and approvers are still
unassigned. The execution plans and blank record systems must be instantiated by the accountable
organizations with genuine signed evidence. They do not approve themselves and do not change the
research-only authorization boundary.

## Priority 0 — Container vulnerabilities

Implemented locally: digest-pinned Wolfi build/runtime, exact Python package versions, non-root user,
read-only-compatible runtime, package manager and shell removal, hash-locked Python dependencies,
Trivy high/critical OS/library gate, configuration/secret scan, CodeQL and retained CycloneDX SBOM.
CI now retains downstream security evidence even if one gate fails and enforces outcomes at the end.
The native ARM image built successfully; read-only/native-library/audit/CPU smoke tests passed; the
runtime contains no `/bin/sh`, BusyBox executable or `apk`; Trivy 0.70.0 reported zero high/critical
Wolfi or Python findings; the repository misconfiguration/secret gate reported zero findings; and a
validated container CycloneDX SBOM was generated. The same controls then passed on a clean, native
AMD64 GitHub runner for commit `bd69363b10373d6d1a627e4cc3a6c0bc386e2498` in quality run
[`29517452489`](https://github.com/VampFay/sem6-miniPwith-withdaBOIS-/actions/runs/29517452489),
including the high/critical image gate, configuration/secret scan, no-shell/no-package-manager smoke
test, numeric non-root-user check and retained CycloneDX SBOM. This resolves the identified
Debian/Distroless container-vulnerability finding for the repository-controlled candidate at the
time of that scan; no vulnerability was suppressed.

Open for medical release: independently repeat the scan against the frozen, signed production image
and deployment infrastructure, review the retained SBOM, and complete penetration, DAST and fuzz
testing. A clean point-in-time scan is not a perpetual assurance claim; recurring monitoring and
documented vulnerability disposition remain mandatory.

## Priority 2 — Model and data evidence

Implemented: verified dataset/checkpoint/training-log evidence generator; tracked hash-bound
snapshot; dataset/model license register; controlled metric dictionary; performance protocol and
patient-clustered SAP; predeclared internal, repeatability, external, prospective, reader and
topology study records; frozen-model and pseudonymous evaluation-manifest templates. The executable
analysis layer records classic AJI, AJI+, PQ/SQ/RQ, object TP/FP/FN, detection precision/recall/F1,
count errors, object FP/FN rates, failure-to-return, per-object/per-region sufficient statistics,
patient/slide/site denominators, tissue/scanner/stain/density/edge/artifact groups and deterministic
site-stratified patient-cluster confidence intervals. A separate-cohort calibration evaluator
records Brier/ECE, failure-detection AUROC/AUPRC, risk-coverage and false reassurance. CI rejects a
draft study presented as executed and the release gate requires completed approved studies and a
frozen model card rather than accepting blank templates. The repeatability/reproducibility analyzer
records count ICC(2,1), within-condition CV, output-hash agreement, Bland-Altman bias/limits and
paired AJI+/PQ shifts across locked conditions.

Open/blocking: PanNuke is declared CC BY-NC-SA 4.0; current derived weights lack commercial
clearance; only 49/150 epochs are recorded. A historical 2,722-patch fold-3 result exists for a
different checkpoint, but it was already observed, used an earlier match boundary and lacks
patient/slide/site hierarchy; it is not an untouched clinical test. The current candidate has no
locked internal patient-level test, independent multi-site validation, prospective validation,
reader/utility result, calibrated uncertainty claim or residual-risk acceptance. Acquire permitted
representative data, train/freeze a new candidate, approve acceptance criteria, and execute the
predeclared studies with qualified pathologists and biostatisticians.

## Priority 3 — QMS

Implemented: quality manual; controlled procedures for documents/records/training, design/risk/change/
release, quality events/CAPA/complaints/vigilance, suppliers/audits/management review; record-field
templates; master document index and automated consistency check.

Open/blocking: appoint legal manufacturer/owners, approve in an eQMS, train personnel, qualify
suppliers/tools, operate procedures to create genuine records, complete internal audit and management
review, close findings and demonstrate effectiveness. Draft documents are not an established QMS.

## Priority 4 — Regulatory strategy

Implemented: US/EU/India planning strategy anchored to current primary sources, claims matrix and
standards plan; uncertain classifications are explicitly not asserted.

Open/blocking: legal manufacturer must freeze intended use/markets; qualified regulatory counsel
must document device/IVD status, classification/product code/rule, predicate/pathway, regulator or
notified-body feedback, evidence requirements and AI Act applicability; obtain actual authorization,
registration, UDI and approved labeling in every launch market.

## Priority 5 — Privacy and cybersecurity operations

Implemented: data/privacy operating model, threat register, secure architecture, vulnerability/CVD,
incident, patch, access/retention/deletion and recovery procedures; existing application controls
cover strict input limits, controlled authentication boundary, model digest and tamper-evident audit.

Open/blocking: site data-flow inventories, DPIAs, lawful basis/consent, BAAs/DPAs/DUAs/transfers,
identity/RBAC/TLS/SIEM/immutable export, penetration and privacy testing, staffed response, restore and
tabletop evidence. Current bearer service authentication is not end-user IAM.

## Priority 6 — Human factors and labeling

Implemented: use specification, task/use-error analysis, formative/summative protocol, draft IFU
content, warnings/limitations, training and competence plan.

Open/blocking: observe representative oncology/pathology/lab users; complete formative rounds;
freeze UI/IFU/training; independently execute summative validation with zero unexplained critical
use errors; approve market-specific labeling and create user competence records.

## Priority 7 — Site deployment qualification

Implemented: risk-based IQ/OQ/PQ, backup/restore/DR/rollback and requalification protocol plus an
objective site acceptance checklist tied to the controlled runtime and load harness. A frozen
topology manifest and direct inference benchmark bind model/topology/input hashes to cold-load time,
map/postprocessing/end-to-end latency, p50/p90/p95/p99/max, sequential throughput, RSS/VRAM and
repeat-output hashes. The API harness separately records concurrent throughput, failures and tail
latency.

Open/blocking: no production site or topology has executed it. Each site must provide approved
infrastructure, run and retain raw IQ/OQ/PQ evidence, close deviations, train users, pass security/
privacy/restore/load/downtime tests and obtain manufacturer/site Quality and Laboratory Director
acceptance.

## Priority 8 — Postmarket operation

Implemented: PMS plan covering data sources, denominators/baseline, signal workflow, complaints,
vigilance, CAPA, field actions, drift, cybersecurity, periodic review, immutable-model change and
stop-use criteria; signal-register template.

Open/blocking: establish staffed intake/on-call and market reporting matrix, privacy-approved
telemetry and alert thresholds, release baseline, site/version inventory, regulator reporting,
periodic reports, complaint/CAPA/recall execution, cybersecurity maintenance and successful incident/
recall simulations. Postmarket readiness must exist before first release, not after launch.
