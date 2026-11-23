# Combined Kaggle and local training

The local collection is now frozen into **18 training, 10 development-test and 5 demo photographs** under `data/local_20261120/split_v1`. The original photographs and original evaluation manifest are preserved. Only the five `sample` photographs are offered in the app gallery; training and test photographs are not exposed there.

The Kaggle feature table and its original train/validation/development-test assignments are preserved. Training combines **2,713 Kaggle training-grain labels** with **17 local training-photo count labels**. The eighteenth training photo, `local_021` (`IMG_20261120_195353.jpg`), has no supplied whole/broken totals and is excluded from supervised fitting.

## What is trained

The existing Kaggle decision tree remains available. A supplemental aspect-ratio threshold is fitted using two kinds of supervision:

1. Local photo totals: average absolute whole-count plus broken-count error, divided by each photo's reference total.
2. Kaggle training labels: class-balanced individual-grain classification error, with a positive source weight selected from 0.1, 0.25, 0.5 and 1.0.

Weight selection uses leave-one-photo-out errors within local training only. The final threshold is fitted with all labelled local training photos and Kaggle training rows, then its model bytes are frozen before test scoring. Neither local test/sample totals nor Kaggle validation/test labels enter fitting. Individual labels are never generated from mixed-photo totals.

The supplemental rule applies to the app's adaptive detector and photos with at least four candidates. Single-grain inputs, the explicit legacy detector and the baseline method retain their original paths. No filenames, known photo totals, or gallery reference counts enter prediction. A local count threshold does not provide calibrated confidence, so no tree confidence is attached to its labels.

## Reproduce locally

```powershell
python src/prepare_local.py
python src/train_local.py --output artifacts/combined_count_reproduction
```

The first command validates and reuses the frozen partition. The second creates a new run; it refuses to overwrite an existing run. Add `--install` to back up and replace `artifacts/model.joblib` when training-only selection improves. Restart with `start.ps1` after installing a new model. Use a new output directory for every run.

Results, thresholds and source-data hashes are in `artifacts/combined_count_v1/report.json` and `calibration.json`. Annotated predictions and unlabelled training-candidate review sheets are in that run's `predictions/` and `crop_review/` folders. The crop CSV labels deliberately remain blank and `verified=false`.

## Adding individual-grain photographs

Put confirmed whole grains in `data/local_grains/whole` and broken grains in `data/local_grains/broken`. Start with at least 20 of each, then expand to different sizes, rice varieties, surfaces and lighting. Take one clearly visible grain per photo, include some short whole grains and long broken fragments, and avoid blur. Keep the grain large enough to inspect without cropping away its ends.

Record a capture/session ID and the actual rice sample for every photo; photos of the same grain or sample should remain in one partition. Folder names supply proposed labels, which still need verification before fully supervised retraining. Do not move the 10 development-test or five demo images, or their crops, into training.

## Evaluation limits

All 33 existing photographs have already been inspected and used in detector development. The new test partition is a **development test**, not a fresh independent final evaluation. Capture/sample group identities are unknown and are left blank. Different photo hashes do not prove independent samples. Collect fresh, separately grouped photos for the final evaluation.

Count errors and broken-percentage errors can be measured from the provided totals. Per-grain accuracy, F1 and a confusion matrix require reviewed individual grain labels. More training images alone do not fix merged or missed detections.


## Measured development results

These results use the fixed 10-photo local development-test partition, with every photo scored. Both methods use the same detections.

| Metric | Previous Kaggle tree | Shape baseline | Combined Kaggle/local rule |
|---|---:|---:|---:|
| Total-count MAE (grains) | 7.20 | 7.20 | 7.20 |
| Whole-count MAE (grains) | 2.90 | 2.80 | 2.80 |
| Broken-count MAE (grains) | 7.90 | 5.40 | 5.40 |
| Broken-percentage MAE (percentage points) | 24.27 | 11.92 | 11.92 |

The combined rule improves on the previous tree and matches the baseline on these 10 photos; it does not establish superiority over the baseline. The fitted aspect-ratio threshold is 2.344606408147154 with Kaggle source-loss weight 0.5. The 12-whole/10-broken training photo returns 12 whole/10 broken; the green 18-whole photo still returns 17 whole/1 broken, and the blue 5-whole/5-broken photo returns 6 whole/4 broken. Matching a photo total does not verify every individual box label.

For the supplemental threshold alone, the existing Kaggle development-test accuracy is 95.70% (broken F1 0.893); the retained source tree remains the single-grain fallback. These are different measurements from multi-grain counting accuracy.


Live verification passed after restarting the app: exactly five demo images are listed; train/test image IDs are blocked; selecting a sample and uploading the same image produces identical grain predictions. The 12-whole/10-broken native upload returns 22 candidates, 12 whole and 10 broken. All 39 automated tests passed.
