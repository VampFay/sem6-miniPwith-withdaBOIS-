---
document_id: MD-OPS-001
revision: 0.1
status: DRAFT RUNBOOK - NOT AUTHORIZED FOR PATIENT CARE
owner: laboratory-operations-owner-unassigned
approver: laboratory-director-unassigned
effective_date: null
---

# Professional Daily-Use Runbook

## Authorization boundary

This runbook becomes effective only for a regulator-authorized claim, manufacturer-released version,
qualified site, approved IFU, competent named user and operational postmarket system. Until all
release gates and site approvals are effective, use is research-only and cannot influence patient
care. The IFU and site SOP override this draft where they are more restrictive.

## Roles and shift handover

- The trained professional verifies case/input suitability, reviews source and overlay, accepts or
  rejects output, and reports errors or suspected harm.
- The shift lead verifies start/end-of-day controls, unresolved cases, downtime and escalation.
- Operations monitors availability, capacity, audit/SIEM, backups, versions and support tickets but
  cannot interpret clinical output unless separately competent.
- Clinical Safety/Quality/Regulatory/Security/Privacy own complaint, incident, stop-use and reporting
  decisions. The Laboratory Director owns site clinical-use authorization.

Handover includes open analyses, rejected/questionable results, downtime reconciliations, alerts,
complaints/incidents, affected release/site scope and any restriction or stop-use instruction.

## Start of day

Complete [DAILY_SAFETY_CHECKLIST.csv](DAILY_SAFETY_CHECKLIST.csv) against the approved site baseline.
Confirm approved URL/release/model/configuration and labeling, readiness, named identity/MFA, audit
and SIEM continuity, time synchronization, capacity/storage, backup/monitoring status, support/on-call
availability and absence of unresolved stop-use/security/clinical notices. Any failed critical check
prevents new analyses and invokes downtime/escalation.

## Per-case workflow

1. Authenticate with a named account; never share credentials or use an administrator account for
   routine analysis.
2. Verify patient/case/specimen association in the validated laboratory system. Use only the approved
   pseudonymous case reference in the application; do not enter direct identifiers into free text.
3. Confirm the specimen, tissue, stain, scanner, magnification/resolution, file/region, image quality
   and artifacts are within approved labeling. Reject unsupported or uncertain inputs.
4. Submit once using locked settings. Do not alter/resave inputs or retry repeatedly to obtain a
   preferred result. Preserve the request ID for any failure.
5. Compare the source image with the complete overlay. Inspect dense, edge, artifact and clinically
   important regions; check for missed, fused, fragmented or spurious nuclei. Output scores are not
   probabilities of malignancy, correctness, diagnosis or calibrated clinical uncertainty.
6. Accept only when the input and result satisfy the approved clinical workflow. Otherwise reject,
   record a coded reason and use the laboratory's validated standard method. The software never
   overrides professional judgment or required reference methods.
7. Export only through the approved workflow. Verify case reference, source hash, release/model,
   settings, result/report hash, timestamp, actor and audit receipt before association with the case.
8. Report suspected malfunction, misleading output, near miss or possible harm immediately. Preserve
   source/result/provenance under site governance; do not send patient data through informal support.

## Error, downtime, and stop-use handling

For authentication, readiness, model/configuration identity, audit/provenance, unsupported input,
processing, storage, network or report errors: stop, preserve the message/request ID, avoid repeated
submission, use the approved standard method and notify the shift lead. Operations records scope and
time, prevents stale/partial result use, restores only from signed artifacts and verified backups,
and reconciles every open case after recovery.

Immediately stop affected use for unverified/wrong model or release, audit-chain gap, result/case
misassociation, uncontained serious clinical risk, material integrity/privacy loss, active
exploitation without adequate control, failed primary safety threshold, or authorized stop decision.
Quarantine affected results and notify the approved contacts. Restart requires documented root cause,
containment, verified recovery, reportability/risk decision, any required requalification and formal
site/manufacturer authorization.

## End of day and periodic controls

Reconcile submitted, completed, rejected, failed, exported and unresolved cases; confirm every
accepted report has provenance and no audit gap; review alerts, access anomalies, storage/capacity,
support events and downtime; hand over open issues. Do not copy patient identifiers into the daily
checklist.

Operations performs scheduled access review, backup restore, certificate/secret rotation, patch and
SBOM monitoring, incident/recall exercises, site/version inventory and requalification. Clinical and
Quality teams review complaints, rejection/use-error trends, performance signals and benefit-risk.
No code, model, threshold, supported input, UI, infrastructure or label change enters production
without controlled impact assessment, verification, authorization and site requalification.
