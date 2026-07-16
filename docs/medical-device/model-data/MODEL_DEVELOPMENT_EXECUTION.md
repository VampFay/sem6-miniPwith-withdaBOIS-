---
document_id: MD-MDE-003
revision: 0.1
status: DRAFT EXECUTION PLAN - NOT EXECUTED
owner: model-and-clinical-leads-unassigned
approver: clinical-safety-and-legal-unassigned
effective_date: null
---

# Model, Data, and Clinical-Evidence Execution

## Release boundary

The existing PanNuke-derived checkpoint remains research-only. It cannot become a commercial or
clinical candidate by renaming, additional testing, or documentation. Commercially permitted,
representative source data and a complete reproducible training record are required for a new
candidate unless qualified counsel documents a different lawful basis in the controlled license
record.

## Data acquisition and acceptance

Before transfer, Legal, Privacy, Clinical, Data, and Quality approve each source in
[DATASET_INTAKE_REGISTER.csv](DATASET_INTAKE_REGISTER.csv). The executed agreement must cover source,
permitted product/research uses, commercial derivatives, sublicensing or distribution, privacy and
ethics basis, permitted locations, retention/deletion, publication, audit, withdrawal, and incident
obligations. A dataset is quarantined until integrity hashes, provenance, patient/site uniqueness,
label method, scanner/stain/specimen metadata, missingness, exclusions, and leakage risks pass.

Acceptance sampling must detect corrupt files, duplicate patients/fields, inconsistent dimensions or
resolution, label schema violations, impossible geometry, annotator identity gaps, hidden site
confounding, and nonrepresentative case selection. Direct identifiers remain outside the development
environment. Every derived file retains source and transformation lineage.

## Reference standard and split lock

Qualified pathologists independently annotate or review under an approved manual. Record training,
blinding, annotation tools, nucleus inclusion/exclusion rules, difficult/artifact handling,
disagreement and adjudication. Report inter-reader agreement without treating consensus as ground
truth certainty.

Lock development, tuning, internal test, external-site, and prospective cohorts by patient and site
before outcome analysis. The model team must not access held-out labels during development. Any
unlock, exclusion, correction, or duplicate removal is contemporaneously justified, versioned, and
assessed for statistical impact.

## Reproducible training and candidate freeze

The training record identifies source commit, immutable environment/locks, dataset manifest and
split hashes, initialization, architecture, transforms, loss, optimizer, schedule, seeds, hardware,
epochs, interruptions/resumes, checkpoints, selection rule, tuning history, deviations, and raw logs.
Training must reach the approved stopping rule; cherry-picking after test review is prohibited.

Candidate freeze creates a signed, immutable bundle containing model weights in the safe supported
schema, SHA-256, architecture/configuration, locked postprocessing, source and dependency identity,
data/split lineage, training receipt, intended use, known limitations, cybersecurity/SBOM evidence,
and rollback identifier. Only this candidate enters formal verification and studies.

## Study execution

Each stage receives a preregistered row in
[CLINICAL_STUDY_REGISTER.csv](CLINICAL_STUDY_REGISTER.csv):

1. locked internal held-out analytical evaluation;
2. independent multi-site external analytical/clinical-performance evaluation;
3. prospective silent or workflow validation in the intended environment; and
4. clinical-utility evaluation when the claim depends on changes to decisions, time, outcomes, or
   workflow.

Protocols predefine endpoints, units, denominators, reference standard, sample-size rationale,
missing/uninterpretable handling, multiplicity, confidence intervals, site/scanner/tissue/artifact and
clinically relevant subgroup analyses, failure taxonomy, sensitivity analyses, acceptance criteria,
deviations, and independent statistical sign-off. All cases and failures are reported. No test or
prospective result is used to tune the evaluated candidate.

## Exit evidence

Exit requires commercial/legal clearance, privacy and ethics approvals, complete provenance, locked
splits, a reproducible frozen model, approved study protocols, passed objective criteria, independent
pathology/statistics reports, benefit-risk linkage, and clinical/regulatory approval. A strong
aggregate metric cannot substitute for missing external, prospective, subgroup, or failure evidence.
