---
document_id: MD-PCS-001
revision: 0.1
status: DRAFT - NOT APPROVED
owner: security-and-privacy-owners-unassigned
approver: legal-manufacturer-unassigned
effective_date: null
---

# Privacy and Cybersecurity Operations

## Scope, responsibility and data boundary

This plan covers source images, identifiers/metadata, predictions, reports, audit records, support
bundles, backups, telemetry, model/data artifacts, credentials and security evidence. Before any
patient data enters the system, the legal manufacturer and each site shall approve a data-flow and
asset inventory identifying controller/processor or HIPAA covered-entity/business-associate roles,
purpose and lawful basis, data categories and subjects, source/destination, location, recipients,
transfers, security controls, retention/deletion, contracts and incident contacts.

The default production design is local/site-controlled processing with no pixels in general logs,
no production data in development, no analytics/advertising trackers, no model training from
clinical use, and no outbound transfer except explicitly approved services. Audit records use a
site pseudonymous case reference and authenticated actor ID; direct patient identifiers remain in
the laboratory system. Support bundles are minimized, reviewed by the site, encrypted and deleted
on closure. Any cloud, remote support, or cross-border flow requires a new privacy/security impact
assessment and contract.

## Privacy governance

The privacy owner completes a DPIA/impact assessment for every market and site before deployment and
after material change. It documents necessity/proportionality, high-risk processing, data-subject
rights, re-identification and linkage risk, automated-decision implications, children/vulnerable
persons where applicable, safeguards, residual risk and consultation/escalation. Data agreements
define instructions, confidentiality, subprocessors, breach assistance, audit, deletion/return and
international transfers. Research and product purposes are separated.

Access follows named accounts, least privilege, role/site segregation, MFA at the identity gateway,
quarterly review and immediate revocation. Shared accounts are prohibited. Retention is a per-record
schedule reconciling medical-device, clinical, laboratory, contractual, privacy and legal-hold
requirements; deletion includes replicas, exports and expiry-controlled backups and produces a
record. Rights requests and corrections are routed to the responsible site/legal entity and must
not silently alter regulated audit or clinical records.

Applicability is determined by counsel, including the [HHS HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html),
[EU GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj), and India's
[Digital Personal Data Protection Rules, 2025](https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa?pageTitle=Digital-Personal-Data-Protection-Rules-2025686cadad39.pdf).
The site matrix records exact breach/reporting deadlines and responsible authority; engineers shall
not infer one jurisdiction's deadline applies elsewhere.

## Security architecture and operating baseline

- Managed TLS terminates at a gateway enforcing OIDC/SAML identity, MFA, role/site policy, request
  size/rate/concurrency/time limits, canonical actor injection and spoofed-header removal.
- The service credential is gateway-to-service only, unique per environment, stored in a managed
  secret system, rotated, never exposed to browser code, logs or images.
- Application and model mounts are read-only. The model digest, release ID and controlled settings
  are mandatory. Runtime is non-root, shell/package-manager-free, network segmented and deny-egress
  by default. Audit storage is durable, restricted, backed up and exported to independently
  protected storage; sequence/hash gaps alert immediately.
- Production hosts use secure boot where available, time synchronization, encrypted volumes,
  endpoint monitoring, hardened admin access, approved patching and no developer tooling.
- CI uses locked dependencies, immutable action/base-image references, SAST, secret/configuration,
  dependency and container vulnerability gates, SBOMs and retained evidence. Release artifacts are
  signed/attested and verified at deployment. The February 2026
  [FDA medical-device cybersecurity guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cybersecurity-medical-devices-quality-management-system-considerations-and-content-premarket)
  is the current US planning anchor.

## Secure development and verification

Security requirements derive from the [threat register](THREAT_REGISTER.csv) and product hazards.
Each release receives architecture/data-flow review, abuse cases, code review, unit/negative/fuzz
tests for parsers and checkpoints, dependency and license review, SAST, DAST, IaC/container scans,
SBOM comparison, credential scan, penetration testing and recovery/rollback exercises proportionate
to impact. Findings include exploitability, patient/clinical impact, affected versions, compensating
controls, owner, due date and independent closure evidence. Clinical safety participates when
availability or integrity could affect care.

## Vulnerability management and coordinated disclosure

Security monitors CISA KEV, NVD/vendor advisories, GitHub/dependency alerts, container OS packages,
Python/npm dependencies, scanners, penetration results, supplier notices and a published security
contact. Intake acknowledges reporters, preserves confidentiality, prohibits retaliation for
good-faith testing, coordinates remediation/disclosure and tracks CVE where appropriate.

Internal targets begin at awareness: potential critical patient-impact/exploited issues receive
on-call triage within 4 hours and containment decision within 24 hours; high within 1 business day;
other findings within 5 business days. Patch deadlines are risk-based and documented, with
out-of-cycle release for uncontrolled risk. Any missed target, active exploitation, unavailable
mitigation or unacceptable patient risk triggers executive/clinical/regulatory escalation and may
suspend use. Regulatory/customer timelines override internal targets when shorter.

## Incident response

1. Detect and open a single incident record; preserve synchronized logs, hashes and chain of custody.
2. Security leads command; Clinical Safety assesses patient impact; Privacy assesses data; Quality
   links complaint/nonconformance/CAPA; Regulatory owns reportability; Operations contains safely.
3. Revoke credentials, isolate affected components, disable analysis or invoke downtime without
   destroying evidence. Never restore an unverified model/build/audit chain.
4. Determine scope, root cause, affected people/sites/versions/data, dwell time and integrity impact.
5. Notify sites, people, regulators and authorities using the approved jurisdiction matrix and
   legally reviewed messages. Awareness time and every decision are recorded.
6. Recover from signed artifacts and verified backups, qualify service, monitor recurrence, complete
   CAPA and update risks, threat model, labeling and postmarket reports.

Tabletop exercises occur at least annually and before first release; technical restore, credential
compromise, malicious upload/model replacement, ransomware/unavailability and audit-corruption
scenarios are exercised and timed.

## Operational evidence and exit

Release requires approved data inventory/flow, DPIA, contracts and transfer assessment; access and
retention schedules; threat model; SBOMs; zero unjustified critical/high findings; independent
penetration report; incident/CVD/patch procedures; staffed contacts; SIEM alerts; key rotation,
backup restore and tabletop records; and site-specific privacy/security acceptance. Policies alone
do not close the PRIVACY or CYBERSECURITY gates.
