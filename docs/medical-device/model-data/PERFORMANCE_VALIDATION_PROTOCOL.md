---
document_id: MD-MDE-004
revision: 0.1
status: DRAFT PROTOCOL - NOT APPROVED OR EXECUTED
owner: clinical-validation-lead-unassigned
approver: pathology-statistics-quality-unassigned
effective_date: null
---

# Model Performance Validation Protocol

## Purpose and release boundary

This protocol controls analytical and clinical-performance evaluation of a frozen Attn-Dist-Net
candidate. It does not authorize patient-care use. A result is release evidence only when its study
protocol and statistical analysis plan (SAP) were approved before label access, the evaluated
candidate and topology were frozen, the dataset was legally and ethically cleared, and independent
reviewers signed the complete report.

The historical PanNuke fold-3 result is research provenance. Its labels and results have already
been observed, its original matching rule used `IoU >= 0.5`, and it lacks patient/slide/site
hierarchy. A corrected rerun must be labelled a historical metric-correction analysis, never an
untouched pivotal test. A future clinical candidate requires a separately locked, custodian-held
internal test cohort.

## Required study order

1. **PV-INT-001 — locked internal analytical validation.** A commercially permitted cohort with
   patient and slide separation from all development and tuning data.
2. **PV-RR-001 — repeatability and reproducibility.** Repeated inference, rescanning, supported
   scanner/topology and operator factors.
3. **PV-EXT-001 — external multi-site retrospective validation.** Independent sites absent from
   development, with blinded execution and an independently curated reference standard.
4. **PV-PRO-001 — prospective silent-mode validation.** Consecutive eligible cases in the intended
   workflow; output cannot affect care.
5. **PV-RDR-001 — reader or clinical-utility validation.** Required when a claim depends on changed
   decisions, time, workflow, or patient-relevant outcome.
6. **PV-TOP-001 — frozen-topology performance qualification.** CPU and each supported GPU topology
   under representative and worst-case loads.

A stage may begin only when its dependencies, ethics/privacy/legal approvals, protocol, SAP,
reference-standard plan, candidate freeze, acceptance criteria, and accountable roles are complete.

## Candidate and analysis lock

Before any protected evaluation label is accessed, record and sign:

- model artifact, SHA-256, safe serialization format, architecture and training receipt;
- source commit, container digest, dependency lock, SBOM and configuration hash;
- preprocessing, resolution, tile/overlap, TTA, postprocessing and all operating thresholds;
- metric implementation version and strict instance match rule (`IoU > 0.5` unless the approved
  intended-use protocol prespecifies another scientifically justified rule);
- uncertainty method and calibrator hash, or an explicit statement that uncertainty is not claimed;
- supported CPU/GPU topology identifiers and deterministic/nondeterministic runtime controls;
- dataset manifest, patient/slide/site split proof and reference-standard revision;
- signed protocol/SAP hashes and the independent label custodian.

Changing any locked item after test review invalidates the candidate for that study. Preserve raw
predictions before scoring. Any unlock, exclusion, correction, rerun or analysis change is a
contemporaneous protocol deviation and receives independent statistical and Quality disposition.

## Data and reference standard

Every record has pseudonymous `site_id`, `patient_id`, `specimen_id`, `slide_id`, `scan_id` and
`region_id`. It also carries tissue/tumor category, stain protocol/batch, scanner/model/firmware,
objective, microns-per-pixel, image-quality/artifact labels, nucleus density, edge status,
eligibility and exclusion reason. Direct identifiers are prohibited in evaluation outputs.

Qualified pathologists follow the approved reference-standard protocol. At least two readers
independently annotate or review the controlled reference set and a qualified third reader
adjudicates disagreements under prespecified rules. Preserve ambiguous/ungradable regions and
report inter- and intra-reader agreement; consensus is not treated as error-free truth.

## Required endpoints

Record raw TP/FP/FN and reference/predicted counts, then derive:

- classic AJI and one-to-one AJI+;
- PQ, segmentation quality (SQ), and recognition quality (RQ);
- object-detection precision, recall and F1;
- signed, absolute and relative instance-count error;
- object-level false-positive and false-negative rates;
- failure-to-return-result and ungradable/excluded rates;
- Dice and IoU as supporting pixel-level endpoints;
- calibrated-uncertainty endpoints when an uncertainty claim is locked;
- end-to-end and component latency, throughput, errors and resource use by frozen topology.

Metric definitions are controlled by [METRIC_DEFINITIONS.md](METRIC_DEFINITIONS.md). Every summary
states numerator, denominator, patient/slide/region/object counts, point estimate, dispersion,
confidence interval, acceptance criterion and disposition.

## Analysis hierarchy and subgroups

The patient is the primary inferential and resampling unit. Report patient-macro, slide-macro and
pooled results without treating dependent patches as independent. Preserve patients' slides and
regions together during resampling and stratify or hierarchically account for site according to the
approved SAP.

Report each supported tissue/tumor, site, scanner, stain protocol/batch, resolution, density,
edge-condition and artifact condition with denominators and uncertainty. Report the worst supported
group and prespecified interactions when sample size permits. Small groups are shown as
underpowered/non-estimable rather than silently pooled or omitted.

## Failure-mode protocol

The controlled taxonomy is
[SUBGROUP_AND_FAILURE_TAXONOMY.csv](SUBGROUP_AND_FAILURE_TAXONOMY.csv). Development-cohort rules
freeze density and quality cutoffs before test access. At minimum distinguish touching/dense nuclei,
image boundaries, internal tile seams, cropped nuclei, blur, folds, pen, debris, bubbles,
compression, stain shift, necrosis, crush/cautery, tearing, empty/background and unsupported input.

For every condition report prevalence, rejection/QC detection, silent plausible-error rate,
object FP/FN, count bias and required clinical disposition. Retain a de-identified, access-controlled
failure gallery; only approved derivatives and hashes belong in Git.

## Repeatability and reproducibility

Repeat unchanged-input inference across cold/warm starts and process restarts. Exact output identity
is required where the runtime is declared deterministic; otherwise quantify mask, instance and count
variation. Reproducibility deliberately varies supported scanner unit/model, rescan, stain batch,
operator, site, CPU/GPU and replica. Analyze paired PQ/AJI+, count coefficient of variation,
intraclass correlation and Bland-Altman bias/limits as approved in the SAP.

## External, prospective and reader studies

External validation uses independent sites with no patient/site overlap or site-specific tuning.
The number of sites and cases comes from a statistician-approved precision/power analysis.
Prospective silent-mode validation enrolls consecutive eligible cases and reports every exclusion,
integration failure, timeout, rerun and distribution shift. Interventional or reader studies require
the applicable regulator/ethics authorization and a design appropriate to the claim, such as a
multi-reader multi-case randomized crossover with reader and case effects.

## Frozen-topology qualification

Each topology manifest records CPU/GPU, memory, driver/runtime, OS, container, storage/network,
threading, concurrency, batch, TTA, tile/overlap and power settings. After controlled warm-up,
record raw timings for cold start, preprocessing, inference, postprocessing, serialization and
end-to-end execution. Report p50/p90/p95/p99/max latency, throughput, errors/timeouts, RAM/VRAM,
utilization, thermal behavior, concurrency scaling and soak/recovery results.

## Exit and stop rules

Stop and block release for leakage, license/ethics defects, reference-standard defects, candidate
drift, missing protected outputs, unapproved analysis changes, failed primary acceptance criteria,
material worst-group failure, unsafe false reassurance, or unresolved clinically relevant anomaly.
Exit requires signed pathology, statistics, clinical safety, Quality and regulatory reports plus
residual-risk acceptance. Passing aggregate model metrics cannot substitute for external,
prospective, human-factors, site or regulatory evidence.

## Controlled analysis invocation

After candidate, dataset, protocol and SAP lock, copy
[EVALUATION_MANIFEST.template.csv](EVALUATION_MANIFEST.template.csv) into the controlled study
workspace and populate only pseudonymous hierarchy and approved subgroup fields. Raw truth and
prediction arrays remain outside Git. Execute:

```bash
python -m scripts.evaluate_clinical_predictions STUDY_MANIFEST.csv \
  --data-root CONTROLLED_DATA_ROOT \
  --output CONTROLLED_OUTPUT/PV-XXX-001 \
  --study-id PV-XXX-001 \
  --candidate-sha256 MODEL_SHA256 \
  --dataset-manifest-sha256 DATASET_MANIFEST_SHA256
```

The command refuses to overwrite an existing evidence directory, hashes every evaluated truth and
prediction array, emits per-object and per-region sufficient statistics, and labels its output as
requiring independent review. Quality-controlled archival, signatures and release disposition
remain external process controls.
