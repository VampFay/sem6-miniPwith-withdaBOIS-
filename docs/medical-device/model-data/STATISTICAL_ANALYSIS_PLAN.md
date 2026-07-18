---
document_id: MD-MDE-005
revision: 0.1
status: DRAFT SAP TEMPLATE - VALUES NOT APPROVED
owner: biostatistician-unassigned
approver: clinical-pathology-quality-unassigned
effective_date: null
---

# Statistical Analysis Plan for Model Performance

## Study-specific fields that must be frozen

No formal analysis may begin until the approved study-specific copy supplies:

- study ID, version, objective, estimand and intended-use claim;
- candidate, dataset, protocol, reference-standard and analysis-code hashes;
- primary/secondary/safety endpoints and success criteria;
- patient/site population, eligibility, sampling method and analysis sets;
- sample-size/precision or power rationale and assumed clustering;
- match threshold, averaging method and all subgroup/failure definitions;
- alpha, confidence level, multiplicity method and interim-analysis rule;
- missing, failed, excluded, ambiguous and ungradable-result rules;
- independent statistician, label custodian, pathology and Quality approvals.

Blank or post-hoc success criteria are a failed protocol, not a neutral result.

## Analysis populations and units

- **Eligible set:** all cases satisfying locked eligibility rules.
- **Full analysis set:** every eligible enrolled/acquired patient, including inference failures.
- **Evaluable reference set:** cases with an adjudicated reference standard; exclusions remain in
  the participant flow and failure analysis.
- **Safety set:** every case on which software execution began.

Patient is the primary statistical unit. Site is the generalizability stratum. Slide, scan, region
and object are nested observations. Report patient-macro and slide-macro endpoints plus explicitly
labelled pooled object/pixel summaries.

## Endpoint calculations

Use raw object matches and counts. The primary metric is selected from the controlled metric
dictionary before study access. Detection precision/recall/F1 are object-level and must not be
substituted with pixel precision/recall. Relative count error is undefined for zero-reference-count
cases; report those separately and never remove them from absolute-error or false-positive analyses.

For each endpoint report estimate, denominator hierarchy, standard deviation or robust dispersion,
two-sided 95% confidence interval, criterion and pass/fail result. A lower confidence bound is used
for minimum-performance criteria and an upper bound for maximum-error criteria unless the approved
protocol states a justified alternative.

## Confidence intervals

The default final method is a deterministic, site-stratified cluster bootstrap with at least 10,000
replicates:

1. sample sites according to the locked external-validity estimand when site is a sampled factor,
   or retain all sites and stratify within site when inference is conditional on participating sites;
2. sample patients with replacement;
3. retain all sampled patients' slides, scans, regions and objects;
4. recompute the complete endpoint from raw sufficient statistics;
5. use the 2.5th and 97.5th percentiles unless a prespecified BCa or exact method is justified.

Use paired resampling for candidate/comparator or assisted/unassisted comparisons. Binomial failure
proportions may use an exact interval only when independence is defensible; otherwise retain the
patient cluster. Record the seed, algorithm version and replicate distribution.

## Multiplicity, missingness and deviations

The primary endpoint has two-sided alpha 0.05 unless otherwise approved. Prespecified co-primary
endpoints and confirmatory subgroup claims require a family-wise or false-discovery control method.
Exploratory analyses are labelled and cannot create new supported claims.

Inference failure is not missing at random: count it in failure rate and apply the locked
worst-case/sensitivity rule to performance. Report missing references, unusable scans, withdrawals,
protocol deviations and post-lock exclusions by reason. No complete-case-only headline result is
permitted without the full analysis set beside it.

## Subgroups and heterogeneity

Report prespecified site, tissue/tumor, scanner, stain, resolution, density, edge and artifact
groups with patient/slide/object denominators and intervals. Report the worst supported group.
Estimate site heterogeneity with a prespecified hierarchical or random-effects method when sample
size supports it. Interaction tests are secondary unless explicitly powered and multiplicity
controlled. Do not infer equivalence from a nonsignificant difference.

## Repeatability, uncertainty and reader studies

For counts, prespecify ICC model, coefficient of variation and Bland-Altman transformation/limits.
For segmentation, use paired AJI+/PQ differences and exact output equality where deterministic
identity is claimed.

Uncertainty evaluation freezes the target event, calibration cohort, calibrator and action
threshold. Report Brier score, calibration intercept/slope where applicable, ECE with binning rule,
failure-detection AUROC/AUPRC, risk-coverage, severe-failure sensitivity and false-reassurance rate.

Reader studies use a statistician-approved multi-reader multi-case or other claim-appropriate model
with reader and case effects, period/order effects, washout and multiplicity controls. Reader time
and workflow endpoints require their own estimands and missing-data rules.

## Independent execution and reporting

The model team produces locked predictions without protected labels. The custodian releases labels
only to the signed analysis environment. The independent statistician runs or verifies the analysis
and signs the immutable report. Preserve raw predictions, sufficient statistics, bootstrap
replicates, logs, environment identity, deviations and review signatures.
