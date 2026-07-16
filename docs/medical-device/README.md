# Medical-Device Readiness File

## Current disposition

**Release blocked.** Attn-Dist-Net is a research system and is not cleared, approved, or validated
for diagnosis, treatment, screening, prognosis, or patient management. The documents here are a
controlled-development framework, not evidence that external clinical or regulatory work has
occurred.

The machine-readable [release manifest](RELEASE_READINESS.json) is fail-closed. A gate may be
marked `approved` only by its accountable human owner, with dated approval and repository evidence.
`./setup.sh release-gate` also verifies controlled runtime configuration, checkpoint identity, and
audit-chain integrity. Software authors must not self-approve clinical, usability, quality, or
regulatory gates without the designated qualified reviewers.

## File map

- [PRIORITY_STATUS.md](PRIORITY_STATUS.md): exact implemented-versus-open status for container,
  evidence, QMS, regulatory, privacy/security, human factors, sites and postmarket work.
- [DOCUMENT_INDEX.csv](DOCUMENT_INDEX.csv): controlled document inventory; validated in CI.
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md): ordered deployment-readiness program with
  owners, dependencies, deliverables, acceptance evidence, and stop/go gates.
- [CODEBASE_AUDIT.md](CODEBASE_AUDIT.md): severity-ranked engineering audit, implemented
  remediations, residual risks, and readiness ratings.
- [INTENDED_USE.md](INTENDED_USE.md): draft purpose, users, population, environment, inputs,
  outputs, limitations, and prohibited uses.
- [QMS_AND_REGULATORY.md](QMS_AND_REGULATORY.md): quality-system work products and regulatory
  decision sequence.
- [SOFTWARE_REQUIREMENTS.md](SOFTWARE_REQUIREMENTS.md): safety-classified software requirements.
- [TRACEABILITY.csv](TRACEABILITY.csv): requirement-to-risk-to-code-to-test links.
- [RISK_REGISTER.csv](RISK_REGISTER.csv): initial ISO 14971-style hazard analysis working file.
- [VERIFICATION_AND_VALIDATION.md](VERIFICATION_AND_VALIDATION.md): verification levels,
  independence, datasets, acceptance criteria, and validation boundaries.
- [CYBERSECURITY.md](CYBERSECURITY.md): threat model, security controls, SBOM/vulnerability and
  incident processes.
- [CLINICAL_EVALUATION.md](CLINICAL_EVALUATION.md): retrospective/external/prospective study plan.
- [DEPLOYMENT_AND_OPERATIONS.md](DEPLOYMENT_AND_OPERATIONS.md): controlled topology, identity,
  audit, backup, rollback, and site acceptance.
- [POSTMARKET.md](POSTMARKET.md): monitoring, complaint, vigilance, drift, and corrective-action
  framework.
- [model-data/MODEL_DATA_EVIDENCE_PLAN.md](model-data/MODEL_DATA_EVIDENCE_PLAN.md): verified current
  evidence, dataset dossier, reference standard, SAP and required study sequence.
- [qms/QUALITY_MANUAL.md](qms/QUALITY_MANUAL.md): proposed QMS and linked controlled procedures.
- [regulatory/REGULATORY_STRATEGY.md](regulatory/REGULATORY_STRATEGY.md): US/EU/India decision and
  authorization plan with claims and standards matrices.
- [privacy-security/PRIVACY_CYBERSECURITY_OPERATIONS.md](privacy-security/PRIVACY_CYBERSECURITY_OPERATIONS.md):
  privacy governance, threat/vulnerability and incident operations.
- [human-factors/HUMAN_FACTORS_AND_LABELING.md](human-factors/HUMAN_FACTORS_AND_LABELING.md): use
  specification, study protocols, draft IFU and training plan.
- [site/SITE_QUALIFICATION.md](site/SITE_QUALIFICATION.md): per-site IQ/OQ/PQ, recovery and acceptance.
- [postmarket/POSTMARKET_OPERATIONS.md](postmarket/POSTMARKET_OPERATIONS.md): surveillance, signal,
  complaint, vigilance, drift and field-action system.

## Required accountable roles

Before design freeze, name at minimum: executive sponsor/legal manufacturer, quality manager,
regulatory lead, clinical safety officer/pathologist, software lead, cybersecurity lead, data
protection officer, biostatistician, usability lead, and independent verification lead. One person
may hold multiple roles only when independence and competence requirements remain satisfied.
