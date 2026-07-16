---
document_id: MD-SQ-001
revision: 0.1
status: DRAFT PROTOCOL - NOT EXECUTED
owner: operations-owner-unassigned
approver: site-quality-and-laboratory-director-unassigned
effective_date: null
---

# Site Deployment Qualification Protocol

## Protocol control and prerequisites

Every site and materially distinct hardware/network/scanner configuration receives its own approved
IQ/OQ/PQ record. Before execution, record protocol/revision, site/environment, responsible and
independent witnesses, planned dates, approved release/container/model/SBOM/configuration hashes,
intended volume and acceptance criteria. Use governed qualification images, never convenience PHI.
Deviations are recorded contemporaneously and independently assessed; testing is not edited after a
failure to create a pass.

Prerequisites are regulatory authorization for the site/market, executed contracts and privacy
assessment, approved release and labeling, trained staff, risk-based infrastructure design, signed
artifacts, rollback/downtime plan, monitored support contacts and approved acceptance checklist.

## Installation qualification (IQ)

Document host make/model/serial, CPU/GPU/RAM/storage, OS/firmware/container runtime, display,
timezone/NTP, network zone, DNS, certificates, identity gateway, SIEM/immutable-log destination,
backup target and external dependencies. Verify:

- image signature and exact digest; container SBOM and vulnerability acceptance; approved model hash;
- non-root UID 65532, read-only application/model/root filesystem, bounded `/tmp`, restricted durable
  audit mount, no runtime shell/package manager, and deny-by-default egress;
- controlled environment values: non-development release ID, approved checkpoint SHA-256, audit
  directory, 32+ character unique service credential, exact HTTPS origins and approved size limits;
- gateway TLS, named identity/MFA, role/site mapping, stripped spoofable actor headers, request limits,
  secret storage/rotation, network segmentation, time, logging/alerts and admin least privilege;
- encrypted backup, retention/deletion, restore credentials, signed rollback artifact and downtime
  method; approved IFU/training/support details at point of use.

Attach redacted configuration, commands/results, screenshots only where necessary, asset inventory,
hashes and deviations. Secrets and patient data must not appear in the record.

## Operational qualification (OQ)

Using the exact production topology, independently execute and retain raw evidence for:

1. `/api/live` returns alive while `/api/ready` reports controlled mode, expected release/model hash,
   locked postprocessing and no sensitive paths; missing/invalid model, config or audit returns 503.
2. Unauthenticated, wrong-token, missing/invalid actor and spoofed gateway identity requests fail;
   authorized requests are attributable; CORS permits only approved HTTPS origins.
3. Valid PNG/JPEG/TIFF within the envelope succeeds and produces source/result hashes, release/model,
   settings, request ID, report and audit receipt. Repetition is characterized and provenance stable.
   Run `python -m scripts.qualify_deployment <image> --url <https-origin> --release-id <id>
   --checkpoint-sha256 <digest>` with the service credential supplied only through the documented
   environment variable; retain its redacted JSON summary. The script also proves unauthenticated,
   wrong-token and missing-actor requests fail before the authorized provenance/audit check.
4. Empty, truncated, mislabeled, malformed, oversized-byte, oversized-pixel, decompression-bomb and
   unsupported inputs fail safely. Controlled threshold/TTA overrides fail.
5. Concurrent requests, rate/timeout/body limits and resource exhaustion behave within predefined
   error and p95 limits. Execute `python -m scripts.load_test ... --max-p95-ms <approved>` using a
   representative qualification image and retain JSON output and host metrics.
6. Audit append/concurrency, exported chain sequence, tamper/truncation detection, storage-full,
   permission loss, log forwarding outage and recovery alert correctly without accepting analysis.
7. Restart, dependency outage, certificate expiry warning, credential rotation, backup/restore,
   signed update, failed update and rollback preserve compatible configuration/audit and fail closed.
8. SAST/SBOM/vulnerability/penetration evidence matches the installed release; port/egress and host
   hardening scans show only approved exposure and no unjustified critical/high issue.

## Performance qualification (PQ)

Representative trained users perform the site's end-to-end workflow with a prespecified set covering
supported tissues/scanners/quality ranges, dense/edge/artifact cases and known failures. Verify case
linkage, input suitability, source-overlay review, result reject/accept, export/provenance, complaint
intake, downtime and recovery. Predictions must match the validated golden-output tolerance for the
exact release. Capture workload volume, latency, failures, user errors and feedback over the approved
duration; no patient-care use occurs during qualification unless separately authorized by protocol.

Site-specific acceptance criteria shall be derived from intended use and risk before execution. At
minimum: 100% critical IQ/OQ controls pass; 100% expected golden cases meet locked tolerance; zero
unexplained critical use errors; zero unauthorized successful request; zero audit-chain gap; zero
unjustified critical/high vulnerability; successful restore and rollback; and load/error limits pass.

## Backup, disaster recovery and continuity

Define RTO/RPO from clinical workflow risk and obtain laboratory approval. Back up configuration
identifiers, audit records and required regulated records; model/application are rebuilt from signed
immutable artifacts rather than untrusted backups. Encrypt and separate backups, restrict/monitor
access, test clean-room restoration and verify audit head/sequence and exact artifact compatibility.
Exercise site/network outage, ransomware, identity outage, audit loss and unavailable support.
Downtime explicitly returns users to the laboratory's validated standard method and reconciles open
cases after restoration.

## Approval, requalification and handover

Operations compiles IQ/OQ/PQ results, raw evidence, deviations, anomaly/risk dispositions, access and
backup records, installed baseline and support roster. Independent verification reviews results;
site Quality, Security/Privacy, Laboratory Director and manufacturer Quality approve acceptance.
Any failure leaves DEPLOYMENT pending. Requalify after model/release/configuration/hardware/runtime/
scanner/network/identity/audit/backup/labeling change according to documented impact; another site's
qualification never transfers automatically.
