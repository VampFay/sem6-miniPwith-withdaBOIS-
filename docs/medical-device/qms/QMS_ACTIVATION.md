---
document_id: MD-QMS-002
revision: 0.1
status: DRAFT ACTIVATION PLAN - NOT AN OPERATIONAL QMS
owner: quality-manager-unassigned
approver: legal-manufacturer-unassigned
effective_date: null
---

# QMS Activation and Objective-Record Plan

## Activation rule

The quality manual and SOP drafts become effective only after the legal manufacturer appoints a
competent Quality Manager, approves the controlled scope and hierarchy, configures an authorized
record/signature system, trains affected personnel, and records effective dates. Backdating,
copying template approvals, or treating repository commits as electronic signatures is prohibited.

## Controlled activation sequence

1. Define QMS scope, legal entities, facilities, products, outsourced processes and exclusions.
2. Approve the quality manual, document hierarchy, terminology, roles, signature authority,
   retention schedule, data integrity controls and regulatory record-access rules.
3. Validate or qualify the eQMS, source control, CI, artifact registry, issue tracker, clinical data
   systems, labeling tools, security scanners and electronic-signature implementation according to
   intended use and risk.
4. Migrate documents with verified identity, revision, status, owner, approver, effective date,
   obsolete-copy handling and change history.
5. Train each role on applicable procedures; assess competence before granting approval, production,
   clinical-data, security-administration or complaint-handling privileges.
6. Qualify critical suppliers before use and execute quality/security/privacy/change-notification
   agreements where applicable.
7. Open genuine design, risk, supplier, training, nonconformance, complaint, CAPA, audit,
   management-review, release and postmarket records as activity occurs.
8. Complete an independent internal audit and management review; correct findings and verify CAPA
   effectiveness before claiming the system is operational.

## Record register

Every controlled record is indexed in [QMS_RECORD_REGISTER.csv](QMS_RECORD_REGISTER.csv) or an
equivalent validated eQMS export. The register is metadata only; objective evidence remains in the
controlled record system. Patient identifiers, credentials, vulnerability exploit details, and
contract-confidential content must not be placed in this repository.

Required record types include:

- organization/role appointment, competence and training;
- document/change approval and obsolete-document disposition;
- design inputs/outputs, reviews, verification, validation and transfer;
- risk analyses, benefit-risk and residual-risk approval;
- supplier qualification, agreements, monitoring and re-evaluation;
- software/model/data release, distribution, installation and revocation;
- nonconformance, complaint, incident, vigilance, CAPA and field action;
- internal/external audit, management review and quality objectives; and
- postmarket, cybersecurity, privacy, site qualification and periodic-review records.

## Training and authorization controls

Training maps role to document/task revision, prerequisites, learning method, assessment, acceptance
score, trainer competence, authorization scope, expiry and reassessment trigger. Access is granted
only after competence is recorded and is revoked upon role change, lapse, prolonged inactivity, or
performance concern. Reading a document without assessed competence is insufficient for a critical
clinical, quality, security, release, or regulatory task.

## Supplier control

Classify suppliers by possible impact on safety, effectiveness, privacy, security, evidence
integrity, regulatory compliance and business continuity. Qualification covers capability, QMS,
security/privacy, data/model license, incident/change notification, subcontractors, audit access,
service levels, continuity, termination, data return/deletion and replacement. Monitor performance
with defined measures; unapproved critical suppliers cannot support release.

## Audit and management review exit

The first full internal audit must sample implementation and records rather than document presence.
Management review evaluates audit/CAPA/supplier/training results, complaints/incidents, clinical and
postmarket evidence, cybersecurity/privacy, process metrics, resources, regulatory changes, quality
objectives and benefit-risk. Exit requires closed critical findings, accepted plans for other
findings, effectiveness evidence, approved resources and a signed determination that the QMS is
implemented—not merely documented.
