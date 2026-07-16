---
document_id: MD-PMS-001
revision: 0.1
status: DRAFT PLAN - NOT OPERATIONAL
owner: quality-manager-unassigned
approver: clinical-safety-and-regulatory-unassigned
effective_date: null
---

# Postmarket Surveillance and Operations Plan

## Objectives and responsibilities

Postmarket surveillance shall actively confirm safety, performance and benefit-risk across released
versions, sites, scanners, tissues, users and time; detect complaints, use errors, drift,
cybersecurity/privacy events and new hazards; meet vigilance/reporting duties; and drive CAPA,
field action and controlled change. Absence of complaints is not evidence of safety.

Quality owns the PMS system and complaint/CAPA records. Clinical Safety assesses harm and signals.
Regulatory owns market-specific reportability, periodic reports and authority communication.
Security/Privacy own cyber/data incidents. Operations owns availability, version inventory and site
communication. The model owner and biostatistician run locked performance/drift analyses. Every role
has a trained deputy and 24/7 path for potential serious harm or active exploitation.

## Data sources and minimum measures

- complaints, incidents/adverse events, field/service tickets, user rejection/override and use errors;
- analysis attempts/success/failure/rejection by approved pseudonymous site and release, with no
  pixels or direct identifiers in central telemetry;
- input-envelope and quality rejections, scanner/stain/tissue/site changes and protocol deviations;
- blinded periodic expert review of governed samples, tracking detection/segmentation/count failure
  modes with denominators and confidence intervals;
- latency, capacity, downtime, readiness failures, audit gaps, backup/restore and rollback outcomes;
- SBOM/vulnerability/exploitation/supplier advisories, penetration findings, access anomalies and
  privacy events;
- published literature, regulator databases, comparable-device actions, customer feedback and
  training effectiveness.

Measures are stratified only when lawful, adequately powered and prespecified. Sites retain linkage
needed for investigation under their governance. Telemetry never becomes automatic training data.

## Baseline, signals and cadence

The approved release record freezes the validation/PQ baseline, expected operating distribution,
metric definitions, denominators, minimum samples, alert and action thresholds. Initial launch
review is at least weekly for operational/security signals and monthly cross-functional safety
review; frequency may change only through documented risk review. A formal aggregate review occurs
at least quarterly and feeds the market-required PMS report/PSUR cadence and annual management
review.

Candidate signals include any death/serious deterioration or near miss; systematic missed/fused/
fragmented nuclei; subgroup/site performance below acceptance; unexpected input shift; repeated
override/use error; audit/provenance gap; wrong model/release; unauthorized access or data loss;
active exploitation; p95/error/availability breach; restore/rollback failure; or statistically and
clinically meaningful trend. Statistical alerting is triage, not proof; Clinical Safety evaluates
clinical relevance and confounding.

## Signal workflow

1. Record the signal in [SIGNAL_REGISTER.csv](SIGNAL_REGISTER.csv) or the eQMS equivalent with
   source, awareness time, denominator, affected scope/version/site and preserved evidence.
2. Immediately triage potential harm, privacy/security, reportability and continued-use risk. Apply
   containment/downtime/quarantine where uncontrolled risk is plausible.
3. Validate the signal using locked definitions and independent review; do not tune the model or
   silently exclude cases. Link related complaints/incidents and assess similar versions/sites.
4. Investigate root cause and update risk, clinical evaluation and threat/use-error analyses.
5. Decide no action with rationale, monitoring, correction, CAPA, training/labeling, software/model
   change, site requalification, customer advisory, field correction/recall or suspension.
6. Regulatory documents each jurisdiction's reportability and deadline from awareness. Track action
   effectiveness and recurrence; close only with Quality and Clinical Safety approval.

## Drift and model performance

Monitor input/data drift using clinically interpretable acquisition/quality features and output/
failure distributions against the frozen baseline. Performance drift requires governed reference
labels and a preregistered analysis; unsupervised distance alone cannot establish clinical
degradation. Alerts are reviewed for site mix, scanner/stain changes, artifacts, workflow and
subgroups. Any threshold breach triggers investigation and may narrow labeling or suspend use.

The production model is immutable. Retraining, recalibration, operating-point or postprocessing
change creates a new model/version and follows design control, license/privacy approval, verification,
clinical/usability/regulatory impact, site requalification and release. No production case enters a
training set without a separately approved lawful/ethical protocol and leakage controls.

## Complaints, vigilance and field action

All support channels are trained to recognize complaints even if the reporter does not use that
word. Record awareness date, event/use context, patient impact, affected artifacts and reporter;
protect privacy and never delay reportability assessment while waiting for complete information.
Regulatory maintains the current per-market decision tree, authority/contact, timelines and report
forms. Quality reconciles distributed/affected units, communications, corrections and effectiveness
for any field action or recall.

## Cybersecurity maintenance

Continuously monitor components and threat intelligence against retained SBOMs. Publish a coordinated
disclosure contact; triage and patch per `PRIVACY_CYBERSECURITY_OPERATIONS.md`; assess patient safety,
exploitability and compensating controls. Validate signed updates and rollback before distribution,
notify sites of actions/urgency, track installation and report cyber incidents as required. Periodic
penetration, restore, incident-tabletop and disaster-recovery exercises are postmarket records.

## Change, periodic review and stop conditions

Every code, dependency, container, model/data, threshold, supported input, infrastructure, UI/report,
label, supplier or claim change receives documented clinical/regulatory/security/privacy/usability/
site impact. Periodic reports summarize exposure, data quality, incidents/complaints, trend and
performance analysis, CAPA/field actions, literature/regulatory changes, benefit-risk and planned
actions with approvals.

Immediately suspend affected use when there is uncontained serious patient risk, wrong/unverified
model, corrupt/unavailable required audit, material unauthorized disclosure or integrity loss,
active exploitation without adequate mitigation, failed primary safety threshold, or regulator/
manufacturer stop decision. Users revert to the approved downtime method. Restart requires root
cause, containment, verified recovery, risk/reportability decision and authorized release/site
acceptance.

## Readiness exit

POSTMARKET remains pending until staffed intake and on-call routes, jurisdictional reporting matrix,
validated telemetry/alerts, privacy-approved data flow, complaint/incident/CAPA/field-action system,
baseline and thresholds, periodic report schedule, CVD/patch capability, version/site inventory,
tabletop and recall simulation, and management approval have objective records.
