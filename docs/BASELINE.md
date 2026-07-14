# Reproduced Baseline

## Run Identity

This baseline is the first complete Attn-Dist-Net training and test-fold evaluation. It is a
binary nuclei instance-segmentation result, not a nuclei-type classification result.

| Field | Value |
| --- | --- |
| Source commit | `4ef30ea` |
| Dataset | `MedOtter/PanNuke` |
| Dataset revision | `8bfedc274e5df3c5afcf258e4d05a968b197e88f` |
| Prepared samples | 7,901 |
| Train / validation / test | fold 1 / fold 2 / fold 3 |
| Encoder | ImageNet EfficientNet-B0 |
| Batch size | 8 |
| Seed | 42 |
| Best validation epoch | 53 |
| Training stop | epoch 73, early-stopping patience 20 |
| Test-time augmentation | disabled |
| Runtime | Python 3.12.13, PyTorch 2.13.0, Apple MPS |
| Dataset manifest SHA-256 | `dbca4c3fb948cd0b23edcef8d56bbf489ecdba212480ad5b82833689cd1ded9f` |
| Checkpoint SHA-256 | `8672b0d2d717d9882f54e87c6a14c2759e04ed2508f4a406529adc04d2cc63f3` |

The checkpoint is excluded from Git. PanNuke and weights derived from it are non-commercial
CC BY-NC-SA 4.0 artifacts; the hash identifies the exact local checkpoint without silently
relicensing or adding a large binary to source control.

## Fold-3 Results

All 2,722 samples in fold 3 were evaluated once with the checkpoint selected only on fold 2.

| Metric | Mean | Standard deviation | 95% bootstrap CI |
| --- | ---: | ---: | ---: |
| Dice | 0.8248 | 0.1336 | [0.8198, 0.8298] |
| IoU | 0.7181 | 0.1476 | [0.7127, 0.7237] |
| Precision | 0.8046 | 0.1434 | [0.7989, 0.8101] |
| Recall | 0.8601 | 0.1391 | [0.8550, 0.8651] |
| AJI | 0.4811 | 0.1673 | [0.4751, 0.4873] |
| PQ | 0.3971 | 0.1951 | [0.3903, 0.4041] |
| Detection F1 / recognition quality | 0.5178 | 0.2160 | [0.5101, 0.5256] |
| Segmentation quality | 0.7365 | 0.1268 | [0.7319, 0.7414] |

The result has strong binary foreground overlap. Instance detection and separation are the
limiting factors: matched instances have segmentation quality 0.7365, but recognition quality
is 0.5178, reducing PQ to 0.3971.

## Evidence

- [Evaluation summary](results/baseline_fold3_summary.json)
- [Per-image metrics](results/baseline_fold3_per_image.csv)
- [Training history](results/baseline_training_metrics.csv)
- [Prepared-array manifest](results/baseline_dataset_manifest.json)
- [Dataset provenance](results/baseline_dataset_provenance.json)

The per-image table is retained because it is required to reproduce aggregate statistics and
confidence intervals. Raw images, masks, checkpoints, TensorBoard events, and runtime logs remain
excluded from Git.

## Comparison Boundary

Published systems do not all use the same aggregation or task definition. For example,
[CellViT](https://arxiv.org/abs/2306.15350) reports three-fold cross-validation, tissue-averaged
binary and multiclass PQ, and nuclei classification. This baseline is one binary fold-3 run with
per-image averaging. The numbers must not be ranked directly until Attn-Dist-Net implements the
official three-fold, per-tissue bPQ/mPQ protocol and a type-classification head.

The fold-3 result is now quarantined from development decisions. New architecture, loss,
postprocessing, and threshold choices use fold 2 only. Fold 3 is evaluated again only for a
predeclared final candidate.
