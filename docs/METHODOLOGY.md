# Methodology

## Scope

Attn-Dist-Net performs binary nuclei instance segmentation in RGB H&E patches. It does not
classify nucleus type, tissue type, malignancy, or patient outcome.

## Data Contract

PanNuke supplies five class-specific instance channels plus background. Preparation merges the
five foreground channels into one globally unique instance-ID map per patch; the background
channel is never interpreted as an instance map. Each prepared sample retains its official fold.

The fixed protocol uses fold 1 for training, fold 2 for validation/model selection, and fold 3
for final evaluation. This prevents random patch-level leakage across the published folds.

The pinned mirror currently prepares 7,901 samples across folds 2,656 / 2,523 / 2,722. Its exact
revision, array hashes, shapes, and dtypes are retained with the reproduced baseline. The
difference from the 7,904 samples described in the CellViT paper must be resolved before claiming
strict protocol parity with that work.

## Targets

The foreground target is `instance_id > 0`. For every nucleus, an Euclidean distance transform
is normalized by that nucleus's maximum distance. Per-instance transforms are merged with a
pixelwise maximum to form the distance target.

## Model

An ImageNet-initialized EfficientNet-B0 encoder supplies five feature scales. Four decoder stages
use skip attention before convolutional fusion. The foreground head predicts logits; the distance
head regresses normalized intra-nucleus distance. Deep-supervision heads regularize training.

The objective combines Dice loss and binary cross-entropy for foreground segmentation, mean
squared error for distance regression, and weighted deep supervision.

## Inference

Large images are processed in overlapping 256-pixel tiles. Hann-window weights blend foreground,
distance, and uncertainty outputs. Optional four-view test-time augmentation averages horizontal
and vertical reflections; mask standard deviation is reported as uncertainty.

Foreground thresholding and minimum-area filtering precede peak detection. Marker-controlled
watershed on the negative distance map produces the final instance labels.

## Evaluation

Semantic evaluation reports Dice, IoU, precision, and recall. Instance evaluation performs
one-to-one IoU matching and reports AJI, panoptic quality, detection F1, segmentation quality,
and recognition quality. The full test report includes per-image values and deterministic 95%
bootstrap confidence intervals.

The current baseline averages metrics per image for one held-out binary fold. Official PanNuke
competitor parity additionally requires all three fold rotations, tissue-aware aggregation, binary
PQ, multiclass PQ, and preservation of the five nucleus classes. Until that protocol is
implemented, published competitor values are context rather than directly ranked results.

The first complete run selected epoch 53 on fold 2 and stopped at epoch 73 after 20 stale epochs.
Its fold-3 evidence is in [BASELINE.md](BASELINE.md). All subsequent model and postprocessing
choices are made on fold 2; fold 3 is reserved for a predeclared final candidate.

## Limitations

PanNuke is a research dataset with a non-commercial license. The project has no prospective,
multi-site clinical validation, calibration study, human-factors validation, regulatory review,
or post-market monitoring. Outputs are research measurements, not diagnoses.

The current model is binary: it does not yet implement the class-aware mPQ task used by leading
PanNuke systems. Its instance-recognition quality is materially lower than its matched-instance
segmentation quality, so stronger separation targets and detection heads are required before
larger encoders alone are justified.
