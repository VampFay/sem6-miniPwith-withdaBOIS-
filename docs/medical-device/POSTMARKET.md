# Postmarket Surveillance and Change Control

Before first authorized deployment, define complaint intake, reportability/vigilance decisions,
field safety action/recall, incident response, customer communication, CAPA, trend reporting,
periodic safety review, and regulator timelines for every market. Train support staff to distinguish
technical failures, cybersecurity events, privacy events, use errors, and potential adverse events.

Monitor by approved site/scanner/tissue/subgroup where legally and statistically appropriate:
input acceptance/rejection, analysis failures, latency, user rejection/override, segmentation error
audits, drift indicators, version adoption, audit continuity, security events, and complaints.
Predefine signal thresholds, minimum sample sizes, investigation workflow, escalation owners, and
actions. Absence of complaints is not proof of safety.

Every change to code, dependencies, model weights, data, preprocessing, postprocessing, supported
input, operating environment, UI wording, report, cybersecurity control, or clinical claim receives
impact analysis. Determine whether regression, analytical, usability, clinical, cybersecurity,
site, or regulatory revalidation is required. Models never learn from production data or update in
place. New model bytes are a new controlled artifact and remain disabled until approved digest,
evidence, labeling, rollback plan, and release record are complete.
