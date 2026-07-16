---
document_id: MD-MDE-001
revision: 0.1
status: DRAFT - NOT APPROVED
owner: model-owner-unassigned
approver: clinical-and-statistics-unassigned
effective_date: null
---

# Model and Data Evidence Plan

## Binding disposition

The current model is a research artifact and must not be used for patient care or commercial
distribution. The verified [research evidence snapshot](RESEARCH_EVIDENCE_SNAPSHOT.json) is the
machine-readable source of current facts. It records the exact dataset, checkpoint, and training-log
hashes. It is regenerated with `python -m scripts.build_model_evidence`; any digest mismatch is a
stop condition.

Current facts are: 7,901 prepared PanNuke patches; train/validation/test folds 1/2/3; checkpoint
SHA-256 `5025fc9c58c5de13fb79686bd84df9ba8dff99c21af56587fe0ddf72bc733835`;
best observed fold-2 validation IoU 0.7163205 and Dice 0.8221833 at logged epoch 43; 49 of 150
configured epochs recorded; and no locked test-fold, external, prospective, or clinical evaluation.
These pixel metrics are not instance-level clinical performance and cannot support a medical claim.

## Dataset dossier requirements

For every development, tuning, test, and external dataset, the data owner shall approve a versioned
record containing:

- source institution, acquisition dates, ethics/consent basis, contract and permitted purposes;
- patient/specimen/slide/patch hierarchy and leakage-prevention unit;
- inclusion, exclusion, missingness, withdrawals, de-identification, retention and deletion;
- tissue, diagnosis, stain, preparation, scanner, objective, resolution, compression, focus,
  artifacts, site, and clinically relevant subgroup distributions;
- reference-standard method, annotator competence, blinding, adjudication, disagreement and change
  history;
- transformations from raw source to immutable analysis set, with code and content hashes;
- intended role (development, tuning, internal test, external test, prospective) and a prohibition
  on reuse across incompatible roles.

Patient, specimen, slide, and site separation shall be tested programmatically before analysis.
Patch-level random splitting is prohibited. Any data exclusion after unblinding is a protocol
deviation and requires independent disposition.

## Reference-standard protocol

Qualified pathologists shall define what constitutes a nucleus for each supported tissue and
artifact condition before annotation. At least two independent readers annotate the reference set;
a third adjudicates disagreements under a prespecified rule. The protocol shall lock annotation
software/version, display and zoom conditions, source-image availability, washout rules, annotation
format, QC sampling, and re-read rules. Inter-reader and intra-reader agreement shall be reported.
Consensus masks are not treated as error-free ground truth; uncertainty and ungradable regions are
preserved and analyzed.

## Statistical analysis plan

The biostatistician shall freeze the estimand, unit of analysis, primary endpoint, safety endpoints,
acceptance limits, sample size, alpha/multiplicity handling, confidence-interval method, missing-data
rule, cluster handling, and subgroup analyses before evaluation data are accessed. At minimum:

- report AJI, AJI+, panoptic quality at the explicitly locked match threshold, detection precision,
  recall/F1, Dice/IoU, count error and failure-to-return-result rate;
- calculate confidence intervals at the patient/slide sampling level, not the patch level;
- report results per site, tissue/tumor type, scanner, stain batch, image quality, density and
  relevant demographic/clinical subgroups, including denominators and uncertainty;
- test repeatability and reproducibility across repeated scans/runs and supported hardware;
- publish all exclusions, protocol deviations, missing outputs and worst-case failures;
- use an independently locked analysis environment and retain raw predictions before unblinding.

Acceptance values are deliberately blank until intended use, clinical harm analysis, comparator,
and regulator strategy are approved. Selecting thresholds after viewing test results invalidates
the test set.

## Required study sequence

1. Acquire commercially and clinically permitted development data; retire PanNuke-derived weights
   from any commercial candidate unless counsel documents a valid alternative permission.
2. Complete training according to a frozen plan and create a new safe-schema inference artifact.
3. Lock preprocessing, architecture, weights, postprocessing and operating point.
4. Run the untouched internal test set once under the approved SAP.
5. Run blinded external multi-site retrospective validation with no site overlap.
6. Run prospective silent-mode workflow validation at representative laboratories.
7. If outputs influence clinical decisions, execute the regulator-agreed reader/utility study.

Any failed primary endpoint, material subgroup degradation, leakage, reference-standard defect,
license defect, or post-lock tuning blocks release and triggers a new version and impact assessment.

## Model card content for the frozen candidate

The approved model card shall identify the legal manufacturer, artifact/hash, architecture and
software versions, training data and legal basis, intended use, unsupported uses, input/output
contract, operating point, calibration status, performance with confidence intervals and subgroups,
known failure modes, human oversight, cybersecurity assumptions, monitoring baseline, and change
policy. It shall distinguish internal validation from independent clinical validation and shall
never call foreground score or TTA disagreement a probability or validated uncertainty estimate.

## Exit evidence

The DATA_LICENSE and CLINICAL gates remain pending until signed license clearance, complete dataset
dossiers, approved protocol/SAP, immutable analysis artifacts, independent statistical report,
clinical evaluation report, and residual-risk acceptance are linked in `RELEASE_READINESS.json`.
