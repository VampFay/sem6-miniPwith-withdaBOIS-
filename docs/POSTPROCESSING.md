# Fold-2 Postprocessing Calibration

## Decision

E01 passed its predefined promotion gate. The calibrated configuration is:

| Parameter | Value |
| --- | ---: |
| Foreground threshold | 0.45 |
| Distance-peak threshold | 0.45 |
| Minimum instance area | 30 px |
| Gaussian sigma | 0.25 |
| Peak window | 25 px |
| Test-time augmentation | disabled |

The configuration is stored in the local `best_iou_calibrated.pt` deployment artifact. Runtime
code reads it from checkpoint metadata; the API and UI do not maintain a separate hidden set of
production defaults.

## Protocol

- Source checkpoint: `8672b0d2d717d9882f54e87c6a14c2759e04ed2508f4a406529adc04d2cc63f3`
- Dataset manifest: `dbca4c3fb948cd0b23edcef8d56bbf489ecdba212480ad5b82833689cd1ded9f`
- Development split: all 2,523 PanNuke fold-2 images
- Coarse-selection subset: 384 deterministic images, seed 42
- Selection metric: mean per-image PQ, then detection F1 and AJI+
- Fold-3 access: none
- Calibrated checkpoint: `fde326a483d9cbb63b1f698b21ff5a9eecd2798f2571dbdc4b4afa7fd3704262`

Raw foreground and distance predictions were computed once and cached locally. Every finalist was
then evaluated on the complete validation fold. The cache identity includes checkpoint, dataset,
index, TTA, and dtype contracts; cache validation also enforces the expected array shape.

## Search

| Stage | Variables | Full-fold winner |
| --- | --- | --- |
| Thresholds | mask 0.35-0.60; peak 0.20-0.45; area 5-30 | 0.45 / 0.45 / 30 |
| Boundary check | peak 0.40-0.60; area 20-60 | 0.45 / 30 confirmed |
| Initial geometry | sigma 0-2; window 3-11 | sigma 2 / window 11 |
| Expanded geometry | sigma 1.5-3.5; window 9-17 | sigma 1.5 / window 17 |
| Window plateau | sigma 1-2; window 15-41 | sigma 1 / window 25 |
| Sigma closure | sigma 0-1.5; window 25 | sigma 0.25 / window 25 |

The final window is an interior point: quality declined at windows 31 and 41. The final sigma is
also interior because both 0 and 0.5 were evaluated. This closes the boundary condition that
invalidated the earlier partial optima.

## Validation Result

| Metric | Original postprocessing | Calibrated | Absolute change |
| --- | ---: | ---: | ---: |
| Dice | 0.82150 | 0.82085 | -0.00065 |
| AJI+ | 0.48641 | 0.62915 | +0.14274 |
| PQ | 0.40436 | 0.60285 | +0.19849 |
| Detection F1 | 0.52719 | 0.74306 | +0.21587 |
| Segmentation quality | 0.73549 | 0.79039 | +0.05490 |

The large gain confirms that the baseline's primary failure was excessive watershed markers and
instance fragmentation. Foreground overlap is effectively unchanged. E01 required a validation
PQ gain of at least 0.02 and achieved 0.19849.

The complete final-stage leaderboard and cache identity are in
[e01_postprocessing_validation.json](results/e01_postprocessing_validation.json). This remains
development evidence, not a new held-out test result. Fold 3 stays quarantined until a
predeclared final model candidate completes the remaining roadmap.

The historical search used the then-current `IoU >= 0.5` PQ implementation. It is valid as a
record of development choices, but the selected configuration must be reconfirmed with the
corrected strict-match evaluator before a controlled release.

## Reproduction

```bash
./setup.sh tune outputs_v2/checkpoints/best_iou.pt \
  --mask-thresholds 0.45 \
  --peak-thresholds 0.45 \
  --min-sizes 30 \
  --gaussian-sigmas 0,0.25,0.5,0.75,1,1.25,1.5 \
  --peak-window-sizes 25 \
  --finalists 7 \
  --calibrated-checkpoint outputs_v2/checkpoints/best_iou_calibrated.pt
```

The threshold, boundary, geometry, and plateau stages above must be repeated when the model
weights, data revision, TTA mode, or instance representation changes.
