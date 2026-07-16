---
document_id: MD-REG-001
revision: 0.1
status: DRAFT - NOT APPROVED OR LEGAL ADVICE
owner: regulatory-lead-unassigned
approver: legal-manufacturer-unassigned
effective_date: null
---

# Regulatory Strategy

## Product definition and decision lock

The current software segments candidate nuclei in RGB H&E patches and produces contours and pixel
morphology for human review. It does not currently ingest whole slides, classify tumor, grade,
diagnose, prognose, or recommend treatment. The legal manufacturer must select one evidence-backed
claim in the [claims matrix](CLAIMS_MATRIX.csv), approve supported tissues/scanners/workflow, and
freeze the intended use before classification. Until then, every pathway below is a planning
hypothesis and the product remains research-only.

The regulatory lead shall document whether the product is medical-device software, an IVD medical
device, an accessory, or non-device research software in each market. Classification must consider
the clinical significance of the output, the health-care situation, whether software drives or
informs a decision, the specimen/analyte context, and the consequences of a wrong result. Calling
the result “assistive” does not lower risk by itself.

## United States

Obtain an FDA product-code and predicate search and a written 510(k)/De Novo/PMA assessment. If no
legally marketed predicate has the same intended use and technological characteristics, obtain a
Pre-Submission before committing to a 510(k). The assessment shall address whether the function is
a device under the FD&C Act and why the clinical-decision-support exclusion does or does not apply;
opaque image segmentation that users cannot independently reproduce should not be presumed exempt.

The operating QMS must meet the FDA QMSR, effective 2026-02-02, which incorporates ISO 13485:2016.
The submission plan shall cover device software documentation, analytical/clinical evidence,
human factors, labeling, biocompatibility only if applicable, and the February 2026 FDA
cybersecurity guidance. Because this connected service contains sponsor-authorized software and can
connect to the internet, the regulatory assessment shall presume “cyber device” obligations under
FD&C Act section 524B until counsel documents otherwise, including an SBOM, vulnerability-management
plan, secure-development evidence, and timely patch process.

Primary sources: [FDA QMSR](https://www.fda.gov/medical-devices/postmarket-requirements-devices/quality-management-system-regulation-qmsr),
[FDA software guidance navigator](https://www.fda.gov/medical-devices/regulatory-accelerator/medical-device-software-guidance-navigator),
and [FDA February 2026 cybersecurity guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/cybersecurity-medical-devices-quality-management-system-considerations-and-content-premarket).

## European Union

Determine MDR versus IVDR scope from the final intended purpose. Image-analysis software acting on
digitized histopathology specimens may require an IVDR analysis; software providing information for
diagnostic or therapeutic decisions may also engage MDR Rule 11 depending on the actual purpose.
Use MDCG 2019-11 rev.1 (June 2025), document every decision branch, confirm classification with a
qualified EU regulatory professional and prospective notified body, and do not assume Class I.

Create the applicable conformity-assessment plan: legal manufacturer and authorized representative,
QMS, general safety and performance requirements checklist, risk/usability/software/cybersecurity
files, performance or clinical evaluation, post-market surveillance, EUDAMED/UDI obligations,
labeling/languages, declaration of conformity, and notified-body review where required. Separately
assess Regulation (EU) 2024/1689: a medical-device AI system can be high-risk when it is a safety
component/product covered by listed harmonization legislation and requires third-party conformity
assessment. Record applicability dates and integration with the device QMS; do not duplicate or
omit controls.

Primary sources: [MDCG 2019-11 rev.1](https://health.ec.europa.eu/latest-updates/update-mdcg-2019-11-rev1-qualification-and-classification-software-regulation-eu-2017745-and-2025-06-17_en),
[MDR](https://eur-lex.europa.eu/eli/reg/2017/745/oj),
[IVDR](https://eur-lex.europa.eu/eli/reg/2017/746/oj), and
[EU AI Act](https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng).

## India

Obtain a written CDSCO Medical Devices Rules, 2017 analysis covering whether the intended software
is a medical device or IVD, risk class, competent licensing authority, import/manufacture route,
test licence or clinical-performance requirements, QMS/site obligations, labeling, registration,
vigilance and change notification. Engage CDSCO or an Indian medical-device regulatory specialist
before collecting pivotal evidence so the study design and sites are acceptable.

Primary source: [CDSCO Medical Devices Rules and amendments](https://cdsco.gov.in/opencms/opencms/en/Acts-and-rules/Medical-Devices-Rules/).

## Required regulator decisions and deliverables

- legal manufacturer, launch order, local representatives/importers and economic operators;
- final intended purpose, indications, users, specimen, environment, outputs and limitations;
- device/IVD status, classification rationale, product code/rule and submission route per market;
- predicate/equivalence strategy and regulator/notified-body meeting questions and minutes;
- evidence map from each claim to analytical, clinical, usability and cybersecurity evidence;
- standards edition/applicability rationale in [STANDARDS_PLAN.csv](STANDARDS_PLAN.csv);
- submission index, deficiency-response owners, registration/UDI/labeling plan and authorization;
- change-assessment rules, including whether an AI predetermined change control plan is suitable.

## Stop/go rules

No pivotal protocol freezes before written pathway feedback where uncertainty could change design.
No marketing claim is used unless its evidence row is approved. No clinical deployment occurs
before the jurisdictional authorization, QMS release, site qualification, approved labeling and
postmarket system are all effective. Regulatory authorization in one jurisdiction does not transfer
to another.
