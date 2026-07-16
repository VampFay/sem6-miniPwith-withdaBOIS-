---
document_id: MD-IVV-001
revision: 0.1
status: DRAFT EXECUTION PLAN - NOT INDEPENDENT VERIFICATION EVIDENCE
owner: verification-lead-unassigned
approver: clinical-safety-and-quality-unassigned
effective_date: null
---

# Risk Management and Independent Verification Execution

## Independence and baseline

Quality approves the verification organization, competence, independence, conflict assessment and
authority to reject the release. The verification lead must not approve work for which independence
is required and they were the sole implementer. Before execution, freeze and record exact source,
requirements, risk file, model, configuration, test code/data, environment, container, dependencies,
SBOM, UI, labeling and intended-use revisions. Results from a different baseline are not release
evidence.

## Risk-management execution

Clinical Safety leads a cross-functional analysis covering normal use, reasonably foreseeable
misuse, incorrect results, automation bias, unsupported specimens, wrong-patient/result association,
availability, audit/provenance, privacy, cybersecurity, maintenance, updates, rollback, servicing,
postmarket and decommissioning. For each hazardous sequence, record severity and probability
rationale, initial risk, inherently safe design controls, protective controls, information for
safety, control verification, new risks introduced, residual risk, benefit-risk where required and
qualified approval.

Risk acceptability criteria are approved before final estimation. Testing cannot lower risk unless
it verifies an effective control. Labeling cannot replace feasible design controls. Aggregate model
metrics cannot close failure-mode, subgroup, usability, site or cybersecurity risks.

## Verification execution layers

- Static/review: requirements and architecture review, trace completeness, code review, dependency
  and license analysis, SAST, secret/configuration and IaC/container analysis.
- Unit/component: algorithms, metrics, parsers, safe checkpoint loading, provenance, audit,
  reporting, configuration, deterministic failure and recovery behavior.
- Integration/system: authenticated API/UI flow, gateway identity, concurrency, rate/size limits,
  full reports, model/configuration identity, audit forwarding, storage-full and dependency faults.
- Security/recovery: independent penetration, DAST, fuzzing, malformed corpus, credential rotation,
  restore, rollback, ransomware, audit corruption and signed-update tests.
- Model/clinical/usability: locked analytical and clinical protocols, golden cases, unsupported and
  difficult cases, summative critical tasks and workflow failure recovery.
- Site: production-topology IQ/OQ/PQ, performance/capacity, downtime, backup/restore and user
  acceptance on the exact installed release.

Each protocol predefines objective acceptance criteria, sample/data identity, raw-output retention,
deviation handling and retest rules. Failed tests remain visible. Retesting follows root cause,
approved correction, impact analysis and a new run identity; results are never edited into passes.

## Anomaly control

Every failure, deviation, unexpected result, security finding, usability issue and known software
anomaly enters [ANOMALY_REGISTER.csv](ANOMALY_REGISTER.csv). Triage considers patient harm,
misleading output, detectability, affected versions/sites/data, exploitability, privacy,
reportability, recurrence and interaction with other anomalies. Closure requires objective evidence
and independent review. Deferral requires rationale, compensating controls, labeling where
appropriate, residual-risk approval and a deadline; “low occurrence in testing” alone is not
adequate.

## Final release-verification report

The report contains the immutable baseline, planned/executed/missed tests, environment and
independence, raw-evidence hashes, results, coverage rationale, all failures/deviations/retests,
open/closed/deferred anomalies, traceability reconciliation, unresolved limitations and a release
recommendation. Quality and Clinical Safety separately approve software verification, overall
residual risk and benefit-risk. Approval does not replace regulatory authorization or site PQ.
