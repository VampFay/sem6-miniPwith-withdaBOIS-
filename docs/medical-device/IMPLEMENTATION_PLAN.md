# Medical-Use Implementation Plan

## Status and governing rule

This plan begins from a **release-blocked research system**. Passing repository checks is necessary
software evidence, but it does not authorize patient use. Work advances only through approved,
version-controlled gates. The quality system of record holds signatures; the repository holds
traceable technical copies. If intended use, claims, markets, input envelope, or workflow changes,
the quality, risk, software, clinical, usability, privacy, cybersecurity, and regulatory impact
assessments must be repeated before work continues.

The accountable legal manufacturer must replace every `*-unassigned` owner in
`RELEASE_READINESS.json`. Gate status may be changed only by the named human approver after every
listed evidence artifact exists and has passed independent review.

## Program sequence

### Phase 0 — Governance and stop-use control

**Accountable:** executive sponsor, quality manager, clinical safety officer.
**Prerequisite:** none.
**Work:** prohibit clinical decision use; inventory every copy, deployment, dataset, checkpoint,
and collaborator; appoint competent quality, regulatory, clinical, privacy, security, software,
statistics, usability, operations, and independent-verification owners; choose the legal
manufacturer and change-control system; train personnel; define escalation and record retention.
**Evidence:** signed project charter, responsibility matrix, training records, system inventory,
research-only notice, document-control SOP.
**Exit:** no uncontrolled instance can receive patient material or influence care; QMS owner accepts
the controlled development baseline.

### Phase 1 — Intended use, claims, markets, and regulatory strategy

**Accountable:** regulatory lead with pathologist and legal manufacturer.
**Prerequisite:** Phase 0.
**Work:** specify analyte/task, specimen preparation, stain, scanner/file formats, supported tissue
and tumor types, patient population, users, environment, input exclusions, output meaning, human
review, contraindications, and whether the product is stand-alone, assistive, or workflow-only;
select launch jurisdictions; obtain written classification and submission strategy; identify
applicable standards and regulator interactions.
**Evidence:** approved intended-use statement, claims matrix, regulatory assessment per market,
standards plan, regulator meeting records where applicable.
**Exit:** `INTENDED_USE` is approved and stable enough to define requirements; the regulatory lead
approves the evidence strategy. Any broader claim returns here.

### Phase 2 — Quality system and lifecycle controls

**Accountable:** quality manager.
**Prerequisite:** Phases 0–1.
**Work:** operate document/record control, design controls, risk management, supplier controls,
configuration and change management, problem resolution, software lifecycle, validation, CAPA,
complaints, audit, management review, release, and postmarket procedures; define independence and
electronic-signature rules; qualify critical suppliers and tools.
**Evidence:** approved SOP set, design/development plan, supplier file, training/competence records,
review minutes, audit schedule, controlled artifact identifiers.
**Exit:** internal quality audit confirms that the system is operating, not merely documented.

### Phase 3 — Data rights, privacy, and governance

**Accountable:** data protection officer and legal owner.
**Prerequisite:** Phase 1 and operating QMS controls.
**Work:** resolve PanNuke and every model/data/library license for the intended commercial use;
create specimen/data lineage; execute site agreements and ethics approvals; establish lawful basis,
purpose limitation, de-identification, access control, retention/deletion, cross-border transfer,
breach handling, and data-subject processes; prohibit PHI in general logs and test fixtures.
**Evidence:** license opinion, data inventory and flow map, DPIA/privacy impact assessment, DUAs/BAAs
or local equivalents, ethics approvals, de-identification validation, retention schedule.
**Exit:** legal and privacy owners approve each dataset and processing route. Unapproved data is
excluded from development and validation.

### Phase 4 — Design inputs, architecture, and risk management

**Accountable:** clinical safety officer and software lead; independent risk reviewers.
**Prerequisite:** Phases 1–3.
**Work:** convert user needs into measurable system/software requirements; define safety class and
system boundaries; complete architecture, data flow, interfaces, failure states, alarm/override
behavior, and deployment assumptions; perform hazard analysis covering wrong segmentation,
omission, false confidence, input shift, mix-up, unavailable audit, misuse, cybersecurity, and
workflow hazards; assign controls and verify bidirectional traceability.
**Evidence:** approved user needs, system requirements, software requirements, architecture,
risk-management plan/file, SOUP inventory, completed traceability matrix.
**Exit:** all unacceptable risks have implementable controls and verification methods; residual-risk
policy and benefit-risk method are approved.

### Phase 5 — Controlled product implementation and design freeze

**Accountable:** software lead and model owner.
**Prerequisite:** approved design inputs and risk controls.
**Work:** implement only traced requirements under review; freeze image decoding, preprocessing,
model architecture/weights, postprocessing, operating point, output semantics, reports, API, UI,
authorization, audit, and error behavior; remove development endpoints and uncontrolled overrides;
create deterministic build and checkpoint procedures; reject legacy artifacts that require unsafe
deserialization; document every known anomaly.
**Evidence:** reviewed source, tests, locked dependencies, signed source commit, checkpoint hash,
model card, build record, anomaly list, change-impact record.
**Exit:** design review approves a versioned candidate. Any model, threshold, dependency, output,
or input-envelope change creates a new candidate and invalidates affected downstream evidence.

### Phase 6 — Independent software and cybersecurity verification

**Accountable:** verification lead and cybersecurity lead, independent of implementation.
**Prerequisite:** frozen candidate.
**Work:** review every requirement/risk control; run unit, property, integration, API, UI, report,
provenance, negative-input, authentication, concurrency, recovery, resource exhaustion, fuzz,
container, installation, backup, and rollback tests; generate an SBOM; scan source, dependencies,
container and IaC; perform threat modeling and penetration testing; disposition every anomaly and
vulnerability with safety impact.
**Evidence:** approved protocols and raw logs tied to source/container/checkpoint digests, coverage
and traceability report, SBOM, scan reports, penetration report, anomaly dispositions, independent
verification report.
Generate the locked Python runtime SBOM and hash receipt with `./setup.sh sbom <evidence-path>`;
retain both artifacts. This is one input to, not a substitute for, the independent release scan.
**Exit:** no unresolved unacceptable risk; no unjustified critical/high vulnerability; every
software requirement and risk control has passing objective evidence.

### Phase 7 — Analytical and model performance verification

**Accountable:** model owner, biostatistician, qualified pathologists; independent analysis review.
**Prerequisite:** frozen candidate and approved statistical plan.
**Work:** rerun corrected AJI, AJI+, strict-threshold PQ, detection and segmentation metrics on locked
data; quantify confidence intervals and failure rates; test repeatability, reproducibility, scanner,
stain, resolution, compression, focus, artifacts, empty/low-cell fields, dense/overlap cases,
out-of-distribution rejection, and worst-case resource behavior; report by site, tissue, tumor,
scanner, stain and relevant demographic/clinical subgroups.
**Evidence:** preregistered analytical protocol/SAP, dataset hashes and lineage, locked analysis code,
complete results, exclusions/deviations, failure gallery, robustness and subgroup reports.
**Exit:** all predeclared analytical acceptance criteria pass without tuning on evaluation data.

### Phase 8 — External clinical evaluation

**Accountable:** clinical lead and biostatistician.
**Prerequisite:** Phases 1–7, ethics/data approvals, regulator agreement where needed.
**Work:** execute independent multi-site retrospective validation with patient/site separation and
blinded reference-standard adjudication; then prospective silent-mode evaluation; if claims imply a
change to diagnosis or care, perform the regulator-agreed reader/utility study; analyze all failures,
missing data, site effects, reader variability and subgroups exactly as preregistered.
**Evidence:** protocols, registrations, approvals, monitoring, locked datasets, deviation log, full
statistical report, clinical safety/benefit-risk report, signed clinical evaluation report.
**Exit:** primary and safety endpoints pass; pathologists, statistics, safety, quality and regulatory
owners accept generalizability and residual clinical risk. A failed primary endpoint stops release.

### Phase 9 — Usability, labeling, and training validation

**Accountable:** usability lead and regulatory lead.
**Prerequisite:** stable workflow and outputs; clinical hazards known.
**Work:** conduct formative and summative human-factors work with representative oncologists,
pathologists and laboratory users; test installation, specimen/input selection, identity handling,
interpretation, review, overrides, failures, degraded/unavailable states, and recovery; validate that
users understand foreground score and TTA disagreement limitations; finalize IFU, limitations,
contraindications, cybersecurity, training and downtime procedures.
**Evidence:** use specification, task/hazard analysis, formative reports, summative protocol/report,
training validation, approved labeling and training materials.
**Exit:** no unmitigated critical-use error; labeling matches only supported evidence and claims.

### Phase 10 — Production deployment qualification

**Accountable:** operations owner with site laboratory leadership.
**Prerequisite:** approved candidate, labeling, software/security evidence.
**Work:** build and sign the exact CPU or separately qualified GPU image; deploy behind managed
TLS/OIDC/RBAC/WAF with read-only application/model mounts and durable restricted audit storage;
validate time, certificates, secrets, network segmentation, backup/restore, disaster recovery,
monitoring, alerting, capacity, p95 latency/error limits and rollback; perform IQ/OQ/PQ at every site
using approved non-patient or governed qualification material.
**Evidence:** signed image/SBOM/provenance, infrastructure configuration, IQ/OQ/PQ records, load and
soak reports, backup restoration and rollback exercises, site acceptance and support roster.
**Exit:** each site passes its predefined acceptance criteria and `./setup.sh release-gate` passes in
the exact controlled runtime. Site qualification cannot transfer implicitly to different hardware.

### Phase 11 — Regulatory submission and release authorization

**Accountable:** regulatory lead, quality manager, legal manufacturer.
**Prerequisite:** all preceding phase evidence.
**Work:** compile the technical/design-history file, resolve regulator questions, complete final
benefit-risk and unresolved-anomaly review, verify production labeling and distribution controls,
obtain required authorization, and conduct formal release review.
**Evidence:** submission and correspondence, authorization where required, signed residual-risk
acceptance, approved release record, final manifest with evidence links and dated approvers.
**Exit:** every required manifest gate is `approved`, disposition is explicitly changed under QMS
change control, and the legal manufacturer signs release. No engineer may perform this approval.

### Phase 12 — Postmarket operation and controlled change

**Accountable:** quality manager, clinical safety, security and operations owners.
**Prerequisite:** authorized release.
**Work:** monitor complaints, incidents, overrides, failures, drift, site/scanner/stain changes,
security advisories, uptime and audit integrity; run periodic safety reports, vulnerability response,
CAPA, backup/restore and disaster exercises; define field correction/recall processes; evaluate every
data/model/software/infrastructure change for regression, clinical and regulatory impact.
**Evidence:** monitoring records, trend reports, complaints/vigilance files, CAPAs, patch decisions,
periodic reviews, revalidation and new release records.
**Exit:** continuous. Breached safety thresholds, corrupt audit, unsupported inputs, material drift,
or a security incident triggers containment and the approved downtime/field-action process.

## Current repository baseline

Implemented controls include strict image decoding and limits, checkpoint hashing, controlled-mode
configuration, service authentication boundary, tamper-evident audit chaining, analysis provenance,
honest output terminology, corrected instance metrics, risk-driven tests, locked CPU dependencies,
pinned CI/container foundations, weights-only versioned training/inference artifacts, a non-root
runtime, a bounded load harness, and a fail-closed release gate. These controls remain development
evidence until independently executed and approved under the QMS against a frozen release candidate.

## Mandatory release command

The final candidate must pass the repository verification workflow and then, inside the exact
production configuration, run:

```bash
./setup.sh release-gate
```

Failure is a stop condition. Editing the manifest to bypass missing evidence is a quality-system
violation, not remediation.
