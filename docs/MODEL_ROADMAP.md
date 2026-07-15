# Model and Product Improvement Roadmap

## Objective

Build a reproducible nuclei analysis system that beats strong reproduced competitors under the
same PanNuke protocol while retaining useful uncertainty, practical WSI throughput, and a strict
research-use safety boundary.

"Best" is defined by measured gates, not a single headline number:

- primary model quality: official three-fold binary PQ and multiclass PQ;
- secondary quality: detection F1, AJI, Dice, per-tissue worst-case PQ, and calibration;
- generalization: external-dataset performance without target-set tuning;
- performance: patches or megapixels per second, peak memory, and WSI completion time;
- reproducibility: three seeds, immutable manifests, exact configs, hashes, and confidence
  intervals;
- product quality: real controls, failure visibility, secure deployment, and no simulated clinical
  claims.

## Current Position

The reproduced baseline reaches Dice 0.8248, IoU 0.7181, AJI 0.4811, PQ 0.3971, detection F1
0.5178, and segmentation quality 0.7365 on one held-out fold. Its main failure is detection and
separation, not the shape quality of correctly matched nuclei.

Strong reference families include:

- [HoVer-Net](https://arxiv.org/abs/1812.06499), which predicts horizontal and vertical offsets to
  separate clustered nuclei;
- [CPP-Net](https://arxiv.org/abs/2102.06867), which uses context-aware polygon proposals and a
  shape-aware objective;
- [PointNu-Net](https://arxiv.org/abs/2111.01557), which decouples keypoint detection from dynamic
  instance segmentation;
- [CellViT](https://arxiv.org/abs/2306.15350), which combines pathology-scale pretraining,
  transformer encoders, weighted sampling, and a HoVer-style decoder;
- pathology foundation encoders such as
  [UNI](https://www.nature.com/articles/s41591-024-02857-3) and
  [CONCH](https://arxiv.org/abs/2307.12914).

Published values are context, not accepted comparison rows. Every competitor must be reproduced
or evaluated with aligned folds, resolution, postprocessing, and metric aggregation.

## Non-Negotiable Experiment Rules

1. Never tune against fold 3. Use fold 2 for all development and lock a candidate before test.
2. Change one major variable per ablation. Compound improvements only after isolated evidence.
3. Run a fast fixed subset smoke test before every full training job.
4. Run at least three seeds for any candidate promoted as an improvement.
5. Report mean, dispersion, confidence interval, throughput, and memory, not only the best seed.
6. Keep current and candidate checkpoints in separate output directories.
7. Preserve failed experiments and negative findings in the experiment registry.
8. Do not compare binary per-image PQ with tissue-averaged bPQ or class-aware mPQ.
9. Use the same 0.25 micrometres-per-pixel resolution when comparing PanNuke methods.
10. Treat external datasets as generalization tests, not extra tuning sets.

## Success Gates

The target is not merely to exceed the current baseline. A release candidate must:

- beat the strongest reproduced competitor by at least 0.01 absolute mean bPQ or mPQ across the
  official three-fold protocol;
- show a confidence interval or paired analysis supporting the improvement;
- reach detection F1 of at least 0.80 without reducing segmentation quality below 0.75;
- improve the lowest-performing tissue groups, not only the global mean;
- pass external generalization on at least MoNuSeg and CoNSeP or MoNuSAC;
- keep an accuracy-oriented model and a deployable efficiency model on the Pareto frontier;
- produce calibrated uncertainty that separates common failures from reliable predictions;
- remain reproducible from a clean checkout and immutable dataset manifest.

The numerical thresholds are promotion gates, not promises. They are revised only from validation
evidence and an aligned competitor harness.

## Phase 0: Benchmark Integrity

### 0.1 Lock the current baseline

- Retain the source commit, dataset manifest, checkpoint hash, training history, and per-image
  metrics already published under `docs/results/`.
- Record wall time, peak memory, model parameters, FLOPs/MACs, and 256/512/1024-pixel inference
  throughput.
- Add a machine-readable experiment index with status, parent experiment, config hash, seed,
  checkpoint hash, and result paths.

### 0.2 Align the PanNuke protocol

- Investigate and document why the pinned mirror contains 7,901 samples while the CellViT paper
  describes 7,904.
- Preserve all five PanNuke instance classes during preparation instead of only the merged binary
  map.
- Implement tissue labels and official tissue-averaged bPQ/mPQ aggregation.
- Run all three train/validation/test rotations and aggregate across folds.
- Add metric parity tests against tiny hand-calculated examples and a trusted reference
  implementation.

### 0.3 Build the competitor harness

- Integrate official inference adapters for HoVer-Net, StarDist/CPP-Net, and CellViT.
- Pin source revisions and checkpoint hashes; record every model's license.
- Normalize magnification, RGB handling, fold IDs, and output instance-map format.
- Measure quality and speed on identical hardware and inputs.
- Do not retrain every competitor initially; first evaluate official compatible checkpoints, then
  retrain the finalists if protocol differences remain.

Exit gate: an apples-to-apples table for quality, memory, model size, and throughput.

## Phase 1: High-Return Postprocessing and Diagnostics

This phase is cheap and directly targets recognition quality.

### 1.1 Diagnose errors

- Partition validation failures into missed nuclei, false positives, merges, splits, boundary
  errors, stain failures, and tiny/dead-cell failures.
- Report metrics by tissue, class, nucleus area, density, stain statistics, and foreground ratio.
- Save representative worst-case overlays selected by metric, never hand-picked success cases.
- Quantify how much PQ loss comes from recognition quality versus segmentation quality.

### 1.2 Calibrate postprocessing on fold 2

- Sweep mask threshold, peak threshold, Gaussian sigma, peak-window size, minimum area, and overlap.
- Optimize validation PQ first, with Dice and false-positive limits as constraints.
- Compare watershed markers from scalar distance, center heatmaps, h-minima, and connected
  components.
- Evaluate four-view TTA and simple checkpoint ensembling against their latency cost.
- Store the chosen postprocessing parameters inside the inference checkpoint, not as hidden
  application defaults.

### 1.3 Improve implementation efficiency

- Replace pairwise full-mask IoU loops with a contingency-table overlap implementation.
- Batch patch inference and postprocessing where practical.
- Add visible evaluation progress and resumable per-image result shards.

Exit gate: statistically meaningful validation-PQ gain without retraining, plus a failure report.

E01 completed on the frozen baseline checkpoint. Fold-2 PQ improved from 0.40436 to 0.60285
without changing model weights, while Dice changed by -0.00065. The selected configuration,
search boundaries, and leakage checks are recorded in [POSTPROCESSING.md](POSTPROCESSING.md).
E02 is next; fold 3 remains quarantined.

## Phase 2: Fix the Instance Representation

The current scalar distance target is insufficiently directional for touching clusters, and its
MSE includes background pixels that can dominate the loss.

### 2.1 Correct the distance objective

- [x] Constrain the distance output to [0, 1] with an explicit checkpointed sigmoid activation.
- [x] Compute Smooth L1 distance loss inside nuclei and separately penalize background leakage.
- [x] Normalize foreground and background independently to prevent area imbalance.
- [x] Log every train and validation loss component to CSV and TensorBoard.
- [ ] Compare the bounded objective with the frozen MSE baseline across three seeds.

E03 uses a background-leakage weight of 0.1 and retains the existing outer distance-task weight of
0.5. These are declared in checkpoint configuration rather than hidden in code. Promotion still
depends on fold-2 PQ and detection F1; implementation completion is not evidence of improvement.

### 2.2 Add separation-aware targets

Run isolated ablations in this order:

1. boundary probability head;
2. center heatmap head;
3. HoVer horizontal/vertical offset heads;
4. discriminative pixel embedding or affinity head;
5. combined center, boundary, and directional representation.

Each head gets target-generation tests, visualization checks, dedicated loss metrics, and a
postprocessor matched to its representation.

### 2.3 Improve the objective

- Compare BCE+Dice with focal Tversky or focal BCE for foreground imbalance.
- Add boundary Dice or level-set loss only after target correctness is proven.
- Use uncertainty-based or gradient-balanced multitask weighting rather than arbitrary constants.
- Keep deep supervision, but supervise each auxiliary head with the target it actually predicts.

Exit gate: detection F1 and PQ improve across three seeds without a material Dice regression.

## Phase 3: Data Sampling and Augmentation

### 3.1 Preserve richer metadata

- Carry tissue type, nucleus class counts, density, and source identifiers into the prepared
  metadata.
- Validate that no slide/source leakage exists beyond the official fold guarantee.

### 3.2 Balance difficult samples

- Add weighted sampling by tissue, rare nucleus class, density, and prior validation loss.
- Cap weights to avoid replacing natural prevalence with extreme oversampling.
- Compare uniform, class-balanced, tissue-balanced, and hard-example sampling.

### 3.3 Strengthen augmentation

- Ablate Macenko/Reinhard normalization versus stain augmentation without normalization.
- Add realistic H&E perturbations, blur, scanner noise, compression, scale, elastic deformation,
  and cutout with pathology-safe bounds.
- Use instance-aware copy-paste only if overlaps and class labels remain anatomically plausible.
- Render augmentation audits so target alignment errors are detected visually and numerically.

Exit gate: gains hold across tissue groups and stain-shift stress tests.

## Phase 4: Encoder and Decoder Search

Do not start here until Phases 1-3 establish a reliable objective and protocol.

### 4.1 Efficient convolutional candidates

- EfficientNet-B3/B4, ConvNeXt-Tiny/Small, and MaxViT-Tiny.
- Match decoder capacity and training budget before comparing encoders.

### 4.2 Transformer and pathology-pretrained candidates

- DINOv2 ViT-S/B as an accessible self-supervised reference.
- UNI or CONCH visual encoders where academic access and license permit.
- CellViT-compatible ViT/SAM-style encoders as a direct architecture reference.
- Compare frozen, gradual-unfreeze, parameter-efficient adapters, and full fine-tuning.

### 4.3 Decoder candidates

- Current attention U-Net, U-Net++, FPN, and HoVer-style multi-branch decoder.
- Use multi-scale feature fusion and sufficient output resolution for tiny nuclei.
- Add type classification only after the binary instance branch is stable.

Exit gate: accuracy gain justifies parameter count, memory, and latency. Keep dominated models out
of the product even when their single best seed is attractive.

## Phase 5: Training Strategy

### 5.1 Controlled 150-epoch experiment

- Preserve the epoch-53 baseline checkpoint.
- Run a separate output directory with early stopping disabled but best-validation checkpointing
  retained.
- Use the full 150 epochs as a learning-curve experiment; never deploy epoch 150 merely because it
  is the last epoch.
- Compare best epoch, final epoch, and exponential-moving-average weights on validation only.

### 5.2 Optimization ablations

- Add warmup plus cosine decay, discriminative encoder/decoder learning rates, and EMA.
- Compare AdamW with a stable reference schedule before introducing newer optimizers.
- Use gradient accumulation and mixed precision on CUDA; verify MPS numerical behavior separately.
- Tune batch size and effective batch size independently.
- Promote hyperparameters through successive halving, then confirm finalists with full budgets and
  three seeds.

### 5.3 Compute strategy

- Keep local MPS for tests, smoke runs, profiling, and short ablations.
- Use a reproducible CUDA worker for parallel seed/fold training and mixed precision.
- Estimate GPU-hours before each sweep and stop candidates through validation-based pruning.

Exit gate: stable training, complete resume state, no non-finite loss, and reproducible multi-seed
results.

## Phase 6: Ensemble, Calibration, and Generalization

- Ensemble only complementary models selected from validation behavior and error correlation.
- Evaluate logit averaging, instance-consensus fusion, and fold ensembles.
- Calibrate pixel and instance confidence with validation data.
- Report expected calibration error, risk-coverage curves, and selective PQ.
- Detect out-of-distribution stain, blur, magnification, and tissue patterns.
- Test zero-shot generalization on MoNuSeg and CoNSeP/MoNuSAC, followed by a clearly separated
  adaptation experiment.
- Add tissue and class fairness tables plus worst-group confidence intervals.

Exit gate: ensemble gain exceeds its latency cost and uncertainty reliably flags failures.

## Phase 7: Tool and Inference Performance

### Accuracy-oriented mode

- TTA, fold ensemble, calibrated uncertainty, and highest-quality postprocessing.
- Full provenance and per-instance export.

### Throughput-oriented mode

- Larger 512/1024-pixel context windows when validation supports them.
- Batched overlapping tiles, channels-last CUDA execution, compiled/ONNX paths, and optional
  TensorRT deployment.
- CuCIM/OpenSlide streaming, bounded caches, backpressure, and resumable WSI jobs.
- Benchmark end-to-end WSI time, not only neural-network forward time.

### Product intelligence

- Real nuclei-type classification from trained labels, not inferred UI labels.
- Quality-control flags for blur, background, stain shift, folds, and unsupported magnification.
- Calibrated uncertainty overlays and a review queue for low-confidence regions.
- Human corrections stored as auditable annotations, never silently mixed into benchmark data.
- Reports that distinguish measured morphology from model confidence and research limitations.

Exit gate: both modes pass deterministic API/UI workflows and publish quality-speed tradeoffs.

## Experiment Queue

| ID | Change | Cost | Primary gate |
| --- | --- | ---: | --- |
| E00 | Lock and profile current baseline | low | reproducibility complete |
| E01 | Fold-2 postprocessing sweep | low | complete: PQ +0.19849; gate passed |
| E02 | TTA and overlap ablation | low | gain/latency Pareto improvement |
| E03 | Foreground-masked bounded distance loss | medium | PQ and detection F1 improve |
| E04 | Boundary head | medium | merge errors decrease |
| E05 | Center + HoVer heads | medium | recognition quality >= 0.65 |
| E06 | Tissue/density weighted sampler | medium | worst-tissue PQ improves |
| E07 | Strong stain/scale augmentation | medium | stress/generalization improves |
| E08 | ConvNeXt/MaxViT encoder screen | high | quality/compute Pareto gain |
| E09 | Pathology foundation encoder | high | multi-seed bPQ gain |
| E10 | Five-class type head and official mPQ | high | valid mPQ benchmark |
| E11 | Three-fold, three-seed finalists | very high | promotion evidence |
| E12 | Complementary ensemble and calibration | high | final quality target |
| E13 | Batched WSI acceleration | medium | throughput target |

## Immediate Execution Order

1. Finish protocol parity and the experiment registry.
2. Profile current inference and vectorize metrics.
3. Run E01 and E02 without touching fold 3.
4. Implement E03 with target/loss visualization and unit tests.
5. Implement E04, then E05 as separate ablations.
6. Add metadata-aware sampling and augmentation studies.
7. Screen encoders only after the instance objective is demonstrably stronger.
8. Add class prediction and official mPQ.
9. Train finalists across all folds and three seeds on CUDA.
10. Lock one final candidate, evaluate once, and publish the full evidence package.

This order spends compute where the baseline evidence predicts the largest return and prevents a
larger encoder from masking target, metric, or postprocessing defects.
