# BigasCheck data card

**Purpose.** Experimental whole-versus-broken rice-grain classification and count-based inspection. Public source: Cristhian Sempertegui, *Dataset de arroz peruano*, https://www.kaggle.com/datasets/cristhiansempertegui/dataset-de-arroz-peruano . Its README credits Cristhian Sempertegui and a Lambayeque rice mill and describes capture during August–September 2023. An explicit redistribution license has not been verified; do not redistribute raw images without confirming it.

**Labels.** `entero` = whole; `quebrado` = broken. `mancha` (stained) and `tiza` (chalky) are excluded from the current integrity classifier. Labels come from source folders and have not received independent per-grain human review. Original capture/session IDs are absent.

| Dataset stage | Whole | Broken | Total |
|---|---:|---:|---:|
| Source integrity categories | 3,352 | 867 | 4,219 |
| Unique, nonconflicting candidates | 3,088 | 791 | 3,879 |
| Accepted for feature extraction | 3,087 | 790 | 3,877 |
| Training | 2,161 | 552 | 2,713 |
| Validation | 463 | 119 | 582 |
| Development test | 463 | 119 | 582 |

Exact duplicates were removed; identical bytes carrying contradictory labels were excluded from both classes. Two additional candidates failed readability or single-region screening. Audit records: `outputs/dataset_audit.json`, `data/peruvian_source.import.json`, `artifacts/excluded_images.csv`, `artifacts/features_and_splits.csv`.

**Images and processing.** Source PNGs are approximately 399–400 pixels per side, generally one grain on black background. EXIF orientation is applied, then RGB conversion, Otsu segmentation/morphology and silhouette measurements. The current shape classifier uses aspect ratio, solidity and area/(major-axis × minor-axis), without RGB or absolute size. Inference offers pale-background thresholding and optional watershed. Those modes are not independently validated on local photographs. No training augmentation was applied.

**Split and leakage.** Approximately 70/15/15 by image with seed 42, deduplicated by exact byte hash. This is not verified capture-level isolation; reencoded or near-duplicate captures may remain. Development-test results have been viewed and samples exposed in the UI. A new, manually verified local set split by capture/sample is required for final evaluation. Three gallery composites use only development-test grains and are not new independent photographs.

**Known gaps.** Crowded/touching grains, pale surfaces, local rice varieties, short intact grains, changing illumination, blur, truncation and different camera scale. No manual multi-grain counts, detection boxes or hand-made masks are yet available for empirical count MAE, mAP, IoU or Dice. Pixel dimensions are not millimeters. Broken percentage is by count, not mass or official grade.
