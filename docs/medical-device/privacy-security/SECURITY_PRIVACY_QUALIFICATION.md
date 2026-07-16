---
document_id: MD-SPQ-001
revision: 0.1
status: DRAFT QUALIFICATION PLAN - NOT EXECUTED
owner: security-and-privacy-leads-unassigned
approver: quality-and-legal-manufacturer-unassigned
effective_date: null
---

# Security and Privacy Qualification Execution

## Scope and evidence integrity

Qualification covers the exact production topology, application/model/container/configuration,
identity gateway, network, endpoints, audit/SIEM, secrets, backups, support path, update service,
telemetry and every patient or regulated-data flow. Repository CI is supporting evidence, not a
substitute for independent testing of the frozen deployed system. Store sensitive reports in the
approved restricted system and reference only redacted identifiers and hashes in
[SECURITY_PRIVACY_EVIDENCE_REGISTER.csv](SECURITY_PRIVACY_EVIDENCE_REGISTER.csv).

## Privacy qualification

Before any patient data are processed, document and approve:

1. data inventory and end-to-end flow for pixels, identifiers, pseudonymous case references,
   predictions, reports, audit, support, telemetry, backups and deletion;
2. legal entity roles, purpose and lawful basis, data-subject categories, high-risk/automated
   processing analysis, jurisdiction and authority contacts;
3. necessity, proportionality, minimization, re-identification/linkage risk, rights handling,
   retention/deletion, legal holds and residual-risk decision in a DPIA or equivalent assessment;
4. BAAs/DPAs/DUAs, confidentiality, subprocessors, transfer mechanisms, incident assistance, audit,
   return/deletion and termination terms;
5. proof that direct identifiers remain in the laboratory system, logs/telemetry exclude pixels and
   direct identifiers, support bundles are reviewed, and production data cannot enter development or
   training without a separate approved protocol; and
6. validated access, correction, export, deletion and backup-expiry procedures that preserve
   regulated audit integrity.

## Production security qualification

Verify named OIDC/SAML identities, MFA, role/site authorization, joiner/mover/leaver controls,
quarterly access review, privileged-session logging and no shared accounts. Prove the gateway strips
spoofable identity headers, uses a unique managed service credential, terminates approved TLS,
enforces request/body/rate/concurrency/time limits and permits only approved origins and routes.

Verify non-root/read-only runtime, signed image/model/configuration identity, deny-by-default egress,
segmentation, encrypted storage/backups, restricted audit storage, independent immutable export,
clock synchronization, endpoint monitoring, secret rotation, secure administration and no
production developer tooling. Attempt wrong/missing identities, privilege escalation, replay,
cross-site access, malicious files, oversized/decompression inputs, dependency outages, audit
tampering, storage exhaustion, model replacement and rollback to an unapproved version.

## Independent testing and finding acceptance

An independent qualified assessor executes architecture review, threat-model review, SAST evidence
review, DAST, authenticated and unauthenticated API/UI penetration, parser/checkpoint fuzzing,
container/host/IaC/cloud/network scans, SBOM/license review and attack-chain testing. Scope,
credentials, rules of engagement, production-data prohibition, test dates, tools, assessor
independence and frozen hashes are approved before testing.

Every finding records evidence, exploitability, patient/clinical impact, affected scope, root cause,
correction, retest and risk acceptance. Release requires zero unjustified critical/high findings.
Risk acceptance must be time-bounded, independently reviewed and include compensating controls,
monitoring, patch date and clinical/regulatory assessment.

## Operational exercises

Before release, execute and time at least: compromised user/service credential; malicious upload;
model/image/configuration substitution; audit corruption or loss; ransomware/site outage; vulnerable
dependency with and without active exploitation; privacy disclosure; backup restore; signed update
failure and rollback. Record detection, triage, clinical safety decision, containment, evidence
preservation, reporting assessment, communications, recovery, site requalification and CAPA.

## Exit evidence

Exit requires approved privacy records/contracts, access and retention evidence, independent test
report and retests, current signed SBOMs, vulnerability disposition, verified alerts and immutable
audit export, key rotation, restore/rollback records, staffed disclosure/incident/patch routes and
successful exercises. Security and privacy approval remains site- and release-specific.
