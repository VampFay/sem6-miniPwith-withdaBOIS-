---
document_id: MD-SOP-002
revision: 0.1
status: DRAFT - NOT APPROVED
owner: quality-manager-unassigned
approver: clinical-safety-and-regulatory-unassigned
effective_date: null
---

# SOP: Design, Risk, Configuration, Change and Release

## Design control

Quality opens a design file and approves the plan, roles, reviews, deliverables and independence.
The team converts approved user needs/claims into testable requirements, identifies architecture and
interfaces, assigns software safety classification, and establishes traceability. Formal reviewers
approve inputs before implementation and outputs before verification. Verification asks whether
outputs meet inputs; validation asks whether the finished product meets user needs and intended use
in representative conditions. Deviations and anomalies are dispositioned before phase closure.

## Risk management

Clinical safety approves the risk plan and scales. The cross-functional team identifies hazards,
foreseeable sequences, hazardous situations and harms across normal use, misuse, faults,
cybersecurity, data/model shift and production. Controls are traced to requirements and objective
tests. Clinical safety approves individual and overall residual risk and benefit-risk; production
information updates the file. Any new unacceptable risk stops work/release.

## Configuration and change

The configuration baseline identifies source commit, lockfiles, build workflow/actions, container
digest, SBOM, model/data hashes, thresholds, infrastructure, labeling and known anomalies. A change
request states reason and urgency and assesses safety, clinical, data/license, privacy, security,
usability, regulatory, validation, labeling, site and postmarket impact. Required reviewers approve
the assessment before implementation. The new candidate receives regression and any triggered
revalidation; no model updates occur in place or learn from production automatically.

## Release

Independent verification confirms protocols/results and traceability. Security accepts no
unjustified critical/high finding. Regulatory confirms authorization and labeling. Operations
confirms signed reproducible artifacts, rollback and qualified sites. Quality verifies all manifest
gates, signatures and exact hashes and issues a release record. Distribution is limited to approved
sites and accompanied by IFU, installation record and support contacts. Failed gates, hash mismatch,
corrupt audit, missing authorization or expired evidence are non-waivable stop conditions.

Required records: design plan, inputs/outputs, review minutes, risk plan/file, traceability,
configuration index, change request/impact decision, verification/validation reports, anomaly list,
release checklist, signed release record and distribution log.
