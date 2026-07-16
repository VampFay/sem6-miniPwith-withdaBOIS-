# Intended Use — Draft, Not Approved

## Unresolved regulatory definition

The final intended use must be approved before clinical dataset selection or pivotal protocol
freeze. The product currently performs binary nuclei instance segmentation and pixel morphology
on RGB H&E image patches. It does not classify nucleus type, grade tumors, identify malignancy,
predict outcomes, recommend therapy, or interpret a whole slide.

The sponsor must decide and document whether the future product is: (a) a research image-analysis
tool with no patient-care claims; (b) a non-diagnostic quantitative aid whose output is reviewed by
a pathologist; or (c) software whose result informs a clinical decision. These are materially
different products and regulatory pathways.

## Draft operating envelope

- Intended user: trained pathologists or qualified laboratory personnel.
- Specimen: formalin-fixed paraffin-embedded H&E tissue; permitted organs and tumor types remain
  undefined until validation data support them.
- Input: scanner- and magnification-controlled RGB image regions meeting pre-analytical quality
  criteria. Whole-slide ingestion is not implemented.
- Output: candidate instance contours and pixel-based morphology, with provenance. Outputs require
  human review and are not calibrated probabilities or diagnoses.
- Environment: authenticated laboratory network, controlled release, approved checkpoint, managed
  workstation/server, validated display, and auditable user identity.

## Prohibited uses until specifically validated and authorized

- autonomous diagnosis, screening, grading, staging, prognosis, therapy selection, or exclusion of
  disease;
- use on unsupported stains, cytology, frozen sections, non-human material, whole-slide files,
  images outside validated resolution/color ranges, or materially corrupted tissue;
- aggregation into a patient-level conclusion without a separately validated clinical algorithm;
- use when provenance, authentication, audit storage, checkpoint verification, or site controls are
  unavailable;
- commercial distribution of PanNuke-derived weights without resolving dataset/model licenses.

## Clinical safety behavior

The user must be able to inspect the source alongside overlays, identify the software/model/input
version, reject an analysis, and revert to the laboratory's standard procedure. The product must
fail closed on malformed input, unapproved model bytes, invalid configuration, authentication
failure, audit-chain corruption, or unavailable required services.
