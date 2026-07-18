---
document_id: MD-MDE-006
revision: 0.1
status: DRAFT CONTROLLED DICTIONARY - NOT APPROVED
owner: model-verification-unassigned
approver: pathology-statistics-unassigned
effective_date: null
---

# Controlled Model-Performance Metric Dictionary

All instance matching uses one-to-one maximum-IoU assignment and a strict `IoU > t` rule. The
default research threshold is `t = 0.5`; a study may use another threshold only when prespecified
and justified. Background label is zero. Nonzero labels are instances.

| Metric | Controlled definition | Empty/reference-zero handling |
| --- | --- | --- |
| AJI | For each reference instance, select its maximum-IoU prediction; sum selected intersections divided by selected unions plus unmatched predicted areas. Prediction reuse follows classic AJI. | Both empty = 1; only one side empty = 0. |
| AJI+ | Hungarian one-to-one assignment over positive IoU; matched intersections divided by matched unions plus all unmatched reference and predicted areas. | Both empty = 1; only one side empty = 0. |
| Detection TP | One-to-one assigned pair whose IoU is strictly greater than `t`. | Zero when no valid match. |
| Detection FP | Number of predicted instances minus TP. | Every prediction is FP when reference is empty. |
| Detection FN | Number of reference instances minus TP. | Every reference is FN when prediction is empty. |
| Detection precision | `TP / (TP + FP)`. | Both sets empty = 1; predictions empty with references present = 0. |
| Detection recall | `TP / (TP + FN)`. | Both sets empty = 1; references empty with predictions present = 1 and FP rate carries the error. |
| Detection F1 / RQ | `2TP / (2TP + FP + FN)`. | Both empty = 1. |
| SQ | Mean IoU of detection-TP pairs. | Both empty = 1; otherwise no TP = 0. |
| PQ | `SQ × RQ`, equivalent to summed matched IoU divided by `TP + 0.5FP + 0.5FN`. | Both empty = 1; otherwise no TP = 0. |
| Signed count error | `predicted_count - reference_count`. | Always defined. |
| Absolute count error | Absolute signed count error. | Always defined. |
| Relative count error | Signed count error divided by reference count. | Undefined when reference count is zero; report separately. |
| Object FP rate | `FP / (TP + FP)`; identical to `1 - detection precision`. | Both empty = 0; no predictions = 0. |
| Object FN rate | `FN / (TP + FN)`; identical to `1 - detection recall`. | Both empty = 0; no references = 0. |
| Failure-to-return | Eligible execution producing no valid controlled result within the locked timeout. | Always included in the full analysis set. |

Pixel Dice, IoU, precision and recall are supporting segmentation endpoints and are never labelled
as object-detection metrics. Pooled detection metrics are recomputed from summed TP/FP/FN; they are
not the arithmetic mean of per-region ratios. Macro results average within the explicitly named
patient or slide unit.

Every report identifies metric dictionary revision, match threshold, aggregation unit, averaging
method, denominator hierarchy, confidence-interval method and behavior for failed/ungradable cases.
