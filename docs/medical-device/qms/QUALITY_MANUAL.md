---
document_id: MD-QM-001
revision: 0.1
status: DRAFT - NOT APPROVED
owner: quality-manager-unassigned
approver: legal-manufacturer-unassigned
effective_date: null
---

# Quality Manual

## Scope and present state

This manual defines the proposed quality system for design, development, validation, deployment,
maintenance and postmarket support of Attn-Dist-Net medical-device software. It is a repository
baseline, not an operational or certified QMS. The designated legal manufacturer shall transfer
approved copies into an access-controlled eQMS, assign competent owners, train personnel, generate
records through actual use, audit effectiveness, and approve the system before regulated evidence
is relied upon.

The quality policy is to release only software whose intended purpose, safety/performance evidence,
regulatory authorization, cybersecurity, privacy, labeling, site controls and postmarket capability
provide documented reasonable assurance of safety and performance. Schedule or commercial pressure
never overrides a stop condition.

## Organization and independence

Executive management owns quality policy, resources and management review. The quality manager may
block release and controls documents, records, audits, CAPA and release authorization. Regulatory
owns classification, submissions, labeling and reportability. Clinical safety owns clinical hazards
and residual-risk/benefit-risk decisions. Software/model owners implement controlled design.
Independent verification approves protocols and results without approving their own implementation.
Security, privacy, statistics, usability, operations and site laboratory owners approve their
domains. Delegation is documented; responsibility remains with the named owner.

## Process architecture

Inputs flow from approved intended use and user needs into design requirements, architecture,
risk controls, implementation, verification, validation, regulatory authorization, production
transfer, site qualification and release. Complaints, incidents, monitoring, audits, supplier
issues, vulnerabilities and changes feed nonconformance/CAPA and design change. Bidirectional
traceability links claim → user need → requirement → hazard/control → implementation → verification
→ validation → labeling → postmarket signal.

The QMS controls at minimum:

- document, record, signature, retention and training control;
- design/development planning, inputs, outputs, reviews, verification, validation and transfer;
- clinical, model/data, usability, cybersecurity and privacy lifecycle evidence;
- risk management throughout the product lifecycle;
- configuration, build, release, distribution, installation, servicing and change control;
- supplier selection, qualification, monitoring and re-evaluation;
- nonconformance, complaints, vigilance, field action, recall and CAPA;
- internal audits, management review and quality-objective monitoring.

## Controlled records and data integrity

Every record has a unique identifier, product/version/site scope, author, event and entry timestamps,
source evidence, review/approval, and change history. Corrections preserve the original entry,
reason, author and time. Electronic signatures are attributable and linked to the signed content.
Access follows least privilege; retention is based on applicable market and product-life rules.
Backups are encrypted, restore-tested and subject to the same retention/deletion controls. Git is a
technical mirror, not the signature or training system of record.

## Design and development controls

Each version has an approved design/development plan defining deliverables, roles, independence,
reviews, interfaces, methods and acceptance criteria. Inputs are measurable and risk-informed;
outputs are verifiable. Formal reviews occur at intended-use freeze, design-input approval, design
freeze, verification completion, validation completion and release. Reviewers record attendees,
competence, materials, issues, actions and approval. Validation uses production-equivalent software
in the actual or simulated intended environment and representative users/populations.

## Risk and release governance

The risk-management plan defines severity/probability scales, acceptability, benefit-risk method,
production-information review and responsible clinical approver. Every unacceptable risk receives
inherent-safety, protective, or information-for-safety controls in that order where practicable.
Risk controls are verified; new risks from controls and aggregate residual risk are evaluated.

Release is fail-closed. The machine-readable manifest must link approved evidence, named owners,
approvers and dates. Quality confirms exact source, dependencies, container, model, configuration,
labeling, site scope, unresolved anomalies and authorization. A failed or missing gate cannot be
waived by editing the manifest; it requires a documented deviation/risk decision where legally and
clinically permissible, never for absent authorization or failed safety evidence.

## Measurement and improvement

Quality objectives include on-time CAPA effectiveness, complaint/reportability timeliness, audit
closure, training currency, supplier performance, escaped defects, security remediation, restore
success and traceability completeness. Management reviews at least annually and after material
safety events. Internal audits follow a risk-based annual program and cover the full system over the
cycle. Management-review and audit records are inspection-ready under the FDA QMSR effective
2026-02-02.

## QMS establishment exit

The QMS gate remains pending until procedures are approved in the eQMS; roles and deputies are
named; personnel are trained and competent; at least one representative design change, supplier
control, nonconformance/CAPA, complaint simulation, release dry run and restore exercise produce
acceptable records; an independent full-system internal audit closes findings; and executive
management signs review and effectiveness acceptance.
