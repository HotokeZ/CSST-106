# Requested updates - 23 November 2026

The running application now uses the curated Kaggle-first gallery and includes a recovery path for dim rice on patterned cloth. Model weights and existing dataset assignments are unchanged.

## Gallery

31 items: 24 original Kaggle images (12 whole, 12 broken), three clearly labelled six-grain Kaggle composites, and four reviewed Local Dataset 2 training crops (two per class). Kaggle appears first. There are no Local Dataset 1 gallery entries. Source and class filters are available. A fresh clone includes these small demo assets and thumbnails; no raw-data download is required to use the picker.

Kaggle originals come from the existing 582-image test partition, which has already been used for development. Local Dataset 2 crops remain training examples and say so in the interface. Neither is a new independent test set. Reference counts are kept separate from predictions and do not feed the detector. Gallery membership, asset hashes and original split labels are checked when loaded.

Rebuild with `python src/prepare_gallery.py` after acquiring the original Kaggle images and reviewed Local Dataset 2 inputs. Existing published gallery assets work without rebuilding. `python -m bigascheck prepare-samples` still prepares the full source partitions; it does not replace the curated picker. Missing gallery data falls back to the Kaggle catalog, never automatically to Local Dataset 1.

## Patterned cloth

The previous dark-background glare filter required 25 intensity levels of local contrast. Dim grains on Local Dataset 1 photo `local_010` failed that threshold. A guarded recovery now looks for smooth, cream-coloured regions relative to the fabric texture, while keeping shape, border and area checks. It runs only after the normal adaptive detector finds fewer than five candidates and predominantly rejects low-contrast regions. It never uses a filename or expected count to decide how many grains to return.

At the default 30-pixel minimum area and 1600-pixel working edge, the measured result changed from 4 candidates to 12. A spatial regression check matches each of the 12 detections to a separately reviewed grain location, once each. The reference is 8 whole / 4 broken; prediction remains 9 whole / 3 broken. Detection recovery does not establish correct breakage classification or mask accuracy.

All 50 local photos were rerun before/after with unchanged weights. Only `local_010` changed its predictions. Blue cloth remains 10 candidates (6 whole / 4 broken, reference 5/5); green cloth remains 18 (17/1, reference 18/0). Remaining label errors are retained as failures.

## Current results and limits

| Set | Images scored | Main count MAE | Broken-percentage MAE |
|---|---:|---:|---:|
| Local Dataset 1, all labelled development photos | 32 of 33 | 3.34 grains | 10.65 percentage points |
| Existing Local Dataset 1 development-test partition | 10 | 3.00 grains | 2.92 percentage points |
| Local Dataset 2, original uncropped training photos | 17 | 29.24 grains | 40.26 percentage points |

Full Local Dataset 2 backgrounds still cause many false detections; reviewed training/gallery crops do not demonstrate full-frame accuracy. The ten-photo development partition has been repeatedly inspected. Source capture groups are unknown. No independent final accuracy, detection mAP or mask IoU is claimed.

The current pooled tree, evaluated on saved Kaggle features by `src/evaluate.py`, scores validation accuracy 95.70%, macro-F1 0.9369; reused test accuracy 96.22%, macro-F1 0.9430. These are per-grain tree results. Multi-grain adaptive inference additionally uses the existing count-supervised aspect calibration, so tree F1 is not a measure of that complete counting pipeline.

## Verification and reproduction

- Current project: 51 automated tests passed, including real patterned/blue-photo spatial regressions.
- Clean isolated dependency install: 51 discovered, 47 passed, 4 skipped because private datasets are deliberately absent; user site disabled. Model loading, home/status, sample listing and sample analysis passed without raw data. This was on the same Windows laptop.
- Running localhost app: all 62 gallery image/thumbnail routes passed, source filters passed, selected-gallery and uploaded identical image bytes produced identical grains. Pattern/blue/green live totals were 12/10/18.
- Current 12-case demo: 9 pass, 3 fail. These are software/demo conditions, not a representative independent accuracy study.

```powershell
python -m unittest discover -s tests -v
python src/evaluate.py --split validation --output outputs/current_validation
python src/evaluate.py --split test --output outputs/current_development_test
python src/test_cases.py --output outputs/current_demo_cases
python src/compare_local_updates.py --output outputs/new_local_comparison
```

The source evaluator/demo-case generator requires the original Kaggle images/full sample catalog. The local comparison requires the existing private Local Dataset 1 manifest/originals/split and reviewed Local Dataset 2 collection. Choose a new comparison output path; earlier evidence is preserved. See `milestone submission/shared/updates_20261123/` for protocol, exact code snapshots, per-photo results, current matrices/failures, test logs, live checks and clean-install metadata. The pre-change detector is included solely to reproduce this development comparison.

This addendum supersedes older numerical summaries for the current application. Earlier PDFs, ZIPs and videos preserve earlier runs and must not be represented as current results.
