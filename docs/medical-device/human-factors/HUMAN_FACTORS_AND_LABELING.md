---
document_id: MD-HFE-001
revision: 0.1
status: DRAFT - NOT VALIDATED OR APPROVED LABELING
owner: usability-lead-unassigned
approver: clinical-and-regulatory-unassigned
effective_date: null
---

# Human Factors, Labeling and Training Plan

## Use specification

Provisional users are pathologists and qualified histopathology laboratory staff who have completed
product training. Use is in an authenticated laboratory network on a site-qualified workstation and
display, with the laboratory's source image and standard procedure available. Users may be under
time pressure and interruptions. Administrators install/restore the system but may not interpret
clinical output unless separately qualified. Patients do not use the product.

The current workflow accepts controlled RGB H&E patches, runs one approved model/configuration,
and displays candidate nuclei overlays, morphology and provenance for human review. Whole-slide,
diagnostic, grading, prognostic, treatment-selection and autonomous use are outside scope. The user
must inspect the source, verify case/input identity and suitability, reject output, document reason,
and continue the validated standard method when the system is unavailable or questionable.

Foreseeable conditions include color-vision and visual-acuity variation, gloves, display variation,
fatigue, interruption, wrong-case selection, unsupported stain/tissue/scanner/resolution, focus or
tissue artifact, dense/overlapping nuclei, empty fields, network/model/audit failure, slow response,
misleading score interpretation, output export and recovery after downtime.

## Use-related risk analysis

The [task analysis](TASK_USE_ERROR_ANALYSIS.csv) is part of the risk file. Each critical task links
use error to hazardous situation/harm, UI/workflow control, labeling/training and validation. The
team shall observe representative users in their real workflow and update the analysis; expert
review alone is insufficient. Information-for-safety is not the sole control when the interface or
workflow can prevent an error.

## Formative evaluation

Conduct iterative contextual inquiry and at least two formative cycles with representative
pathologists, laboratory users and administrators across intended site types and experience levels.
Use production-like prototypes and realistic benign, difficult, unsupported, erroneous and failure
scenarios. Capture task success, close calls, recovery, time, assistance, comprehension, workload,
observations and interview evidence. Root-cause every error and trace changes through risk/change
control. Formative findings cannot be counted as summative evidence.

## Summative validation protocol

After UI, workflow, IFU and training are frozen, an independent team runs the approved protocol in
representative environments without coaching. Sample size and participant strata require a
documented rationale. Every participant performs all applicable critical tasks, including identity
and suitability checks, source/overlay review, interpretation of foreground score and TTA
disagreement, rejection/override, export/provenance, authentication failure, unsupported input,
service/audit/model failure, downtime and recovery.

Predefine task-level success and comprehension criteria, assistance rules, critical-use-error
acceptance and statistical treatment. The release condition is zero unexplained or unmitigated
critical-use errors; any observed critical error receives root-cause analysis and clinical risk
assessment, and design changes trigger repeated affected validation. Report all participants,
deviations, failures, close calls and subjective findings, not only successes.

## Draft labeling / instructions for use

The following is development text and must not be distributed as approved IFU:

**Device status:** research software; not authorized for diagnosis or patient management.

**Provisional future purpose:** display candidate nuclei instance segmentations and pixel-based
morphology from validated H&E image regions as an aid for review by a qualified pathologist. Exact
tissues, scanners, resolution and clinical claim are TBD and may only reflect completed evidence.

**Output meaning:** contours are model-generated candidates. Foreground score is not probability of
malignancy or correctness. TTA disagreement is augmentation variance, not calibrated clinical
uncertainty. A successful result does not certify input suitability or absence of missed/fused/
fragmented nuclei.

**Warnings:** do not use autonomously; do not use an unsupported specimen, stain, tissue, scanner,
file, resolution or artifact condition; do not rely on output when case identity, approved release,
model hash, audit readiness or authentication cannot be verified; incorrect segmentation may alter
counts/morphology; always review source and follow the site's standard procedure.

**Contraindications/prohibited use:** frozen sections, cytology, non-H&E or non-human material,
whole-slide files, patient-level diagnosis/grade/stage/prognosis/therapy, screening or exclusion of
disease until specifically validated and authorized.

**Procedure:** authenticate; verify patient/case linkage in the laboratory system without copying
direct identifiers into the app; confirm input envelope and image quality; submit once; compare
source and overlay; inspect dense/artifact/edge regions; accept or reject; export with release/model/
input/result provenance; record rejection or suspected malfunction; use downtime method if needed.

**Errors and downtime:** do not repeatedly alter files or thresholds to obtain a preferred result.
For authentication, readiness, model, audit, unsupported-input, processing or provenance errors,
stop analysis, preserve message/request ID, use the approved laboratory method and contact support.
Potentially harmful output is a complaint and must be reported immediately.

**Cybersecurity:** access only through the approved site URL and named account; never share
credentials; do not upload from unmanaged media; report suspicious access, altered model/release
identity or audit gap; install only signed updates approved by the site.

## Training and competence

Training covers intended use/limitations, supported inputs, case linkage, source-overlay review,
scores, common failure gallery, acceptance/rejection, provenance/export, privacy, cybersecurity,
complaints, downtime and recovery. Administrators additionally train on IQ/OQ, identity, secrets,
backups, monitoring, updates and rollback. Competence requires observed critical-task completion and
a knowledge assessment at a predeclared score; failed learners retrain and reassess. Requalification
occurs after material change, prolonged inactivity or performance concern. Training effectiveness is
validated during summative testing and monitored through use errors and complaints.

## Exit evidence

USABILITY and LABELING remain pending until the use specification and analysis are approved,
formative issues are closed, frozen summative protocol/report passes, training effectiveness and
competence records exist, labeling is evidence-consistent and regulatory-approved, and every site
has trained the intended roles.
