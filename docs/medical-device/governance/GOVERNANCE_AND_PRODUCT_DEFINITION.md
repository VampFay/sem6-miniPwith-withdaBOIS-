---
document_id: MD-GOV-001
revision: 0.1
status: DRAFT EXECUTION PLAN - NOT APPROVED
owner: executive-sponsor-unassigned
approver: legal-manufacturer-unassigned
effective_date: null
---

# Governance and Product-Definition Execution

## Purpose and stop condition

This workstream establishes who is legally accountable and what product is being built. No clinical
study freeze, regulatory classification, production release, marketing claim, or patient-care use is
permitted while the legal manufacturer, initial market, intended use, and accountable gate owners
remain unassigned or unapproved.

## Required decisions

The executive sponsor opens one controlled row in [DECISION_REGISTER.csv](DECISION_REGISTER.csv) for
each decision below and attaches signed evidence in the eQMS or approved record system:

1. legal manufacturer name, registered address, executive authority, insurance, and applicable local
   representatives, importers, or economic operators;
2. initial launch jurisdiction and explicitly deferred jurisdictions;
3. device boundary, supplied components, deployment model, operators, customers, and support model;
4. intended purpose, indications, patient/specimen population, trained users, use environment,
   inputs, outputs, clinical workflow, exclusions, contraindications, and human-review obligation;
5. exact supported tissues, stains, scanners, magnification/resolution, file types, quality envelope,
   and whether whole-slide use is excluded;
6. claim selection and evidence required for each claim, linked to `CLAIMS_MATRIX.csv`;
7. accountable and deputy assignments for Quality, Regulatory, Clinical Safety, Privacy, Security,
   Software, Model/Data, Biostatistics, Usability, Verification, Operations, and Postmarket;
8. independence and conflict-of-interest assessment for approvers and verification personnel;
9. record system, electronic-signature method, retention rules, and document-control authority; and
10. program funding, qualified suppliers, study sites, stop authority, and launch governance.

## Product-definition review

Clinical, regulatory, model/data, software, usability, security/privacy, operations, and quality
owners jointly review the draft `INTENDED_USE.md`. The review must demonstrate that every claimed
input and output is implemented, every population and acquisition condition can be represented in
licensed evidence, every foreseeable incorrect result has a safe workflow, and every claim can be
tested with objective acceptance criteria. Ambiguous phrases such as “assistive,” “AI powered,” or
“clinically accurate” are rejected unless the precise user action and evidence are defined.

The approved definition receives a revision and effective date. Any later change to claims,
population, specimen, scanner, input, output, workflow, user, environment, automation, or decision
significance enters design and regulatory change control before implementation.

## Governance cadence and escalation

- Weekly program review: blockers, dependencies, study/supplier status, risk and overdue actions.
- Monthly design/quality review: traceability, anomalies, CAPA, cybersecurity, clinical evidence and
  benefit-risk.
- Formal phase gates: intended-use lock, design input, model/data freeze, verification readiness,
  pivotal-study readiness, submission, production release, and site go-live.
- Any owner may stop work for uncontrolled patient, privacy, security, legal, evidence-integrity, or
  regulatory risk. Only the documented authority for that domain may accept or escalate the risk.

## Exit evidence

Exit requires assigned competent owners and deputies, approved conflict/independence records, signed
legal-manufacturer and market decisions, approved intended use and claims, frozen operating envelope,
effective document-control system, and approved phase-gate/RACI records. Repository authors cannot
self-appoint the manufacturer or approve this workstream on its behalf.
