---
document_id: MD-SGL-001
revision: 0.1
status: DRAFT EXECUTION PLAN - NO SITE QUALIFIED
owner: operations-owner-unassigned
approver: site-quality-and-laboratory-director-unassigned
effective_date: null
---

# Site Qualification and Go-Live Execution

## Site dossier and prerequisites

Create one controlled dossier and one [SITE_EXECUTION_REGISTER.csv](SITE_EXECUTION_REGISTER.csv) row
for each materially distinct site/topology. Record legal entity, laboratory, authorization scope,
contacts and deputies, hardware/scanner/display/network/identity/audit/backup/SIEM architecture,
data flows/contracts, release/model/container/configuration/SBOM/label hashes, intended workload,
RTO/RPO, support hours and downtime method. Another site's qualification cannot be copied.

Execution starts only after regulatory authorization or separately approved investigational use,
effective QMS release, privacy/security approval, signed artifacts, approved labeling, trained staff,
accepted infrastructure and a preapproved `SITE_QUALIFICATION.md` protocol with objective criteria.

## IQ/OQ/PQ execution and evidence

- IQ records assets, versions, certificates, time, segmentation, least privilege, read-only mounts,
  non-root runtime, restricted egress, secrets, audit/SIEM, backup, signed artifact verification,
  labeling/support availability and deviations.
- OQ retains raw results for readiness/fail-closed behavior, named identity/RBAC, wrong/missing actor,
  CORS/TLS, valid and hostile inputs, provenance/audit, concurrency/load, storage/audit/model/network
  faults, alerting, credential rotation, signed update, restore and rollback.
- PQ has representative trained users execute the complete site workflow with prespecified supported,
  difficult, artifact, edge, known-failure, complaint and downtime cases. Predictions match frozen
  golden tolerances and the intended workload meets approved latency/error/capacity criteria.

Use `python -m scripts.qualify_deployment` and `python -m scripts.load_test` where applicable, but
retain their version, command parameters, redacted output and host evidence. Automation does not
replace independent observation or approval.

## Deviations and acceptance

Record failures contemporaneously; do not edit protocols or evidence to create a pass. Deviations
identify root cause, patient/privacy/security impact, affected controls, correction, retest,
requalification scope and independent disposition. Minimum acceptance remains: all critical controls
pass, no unauthorized success, no audit gap, no unjustified critical/high vulnerability, golden
cases pass, zero unexplained critical use errors, and restore/rollback/downtime/load tests pass.

## Controlled go-live

Manufacturer Quality, site Quality, Security/Privacy, Operations and Laboratory Director approve the
installed baseline, deviations, trained-user list, support/on-call routes, monitoring, complaint and
incident contacts, backup/restore, downtime and rollback. Operations enables production access only
after all signatures. Start with the approved limited rollout, enhanced monitoring and reconciliation
of the first cases; stop-use authority is published to all shifts.

Any model/release/configuration, scanner, hardware, runtime, gateway/identity, network, audit/SIEM,
backup, labeling, intended-use or workflow change receives impact assessment and risk-based
requalification before use.
