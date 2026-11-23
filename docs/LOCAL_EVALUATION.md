# First frozen local-photo evaluation - 20 November 2026

The supplied `Bigas Check Local Photos.zip` contains **33 photographs**, not 30. There are 32 filename-count references: 396 whole and 181 broken grains. The remaining photo, `IMG_20261120_195353.jpg`, is unscored because counts are missing. Whole-only filenames are interpreted as zero broken, pending user confirmation. Labels/counts have not been independently reviewed.

Physical sample IDs and capture groups remain blank/unknown. File IDs `local_001` etc. do not identify independent physical rice samples. The whole collection remains outside training. No capture-independent confidence interval or train/test split is invented. There are no exact-byte duplicates within the supplied photos or with the published source feature-table images.

## Frozen protocol

The original images are preserved under `data/local_20261120/originals`. EXIF-transposed RGB working JPEGs use a fixed maximum 1600-pixel edge (LANCZOS, quality 95). Automatic background and watershed are enabled; remaining parameters come from the existing saved shape model. This is an evaluation of these standardized working images, not a native-resolution web benchmark. Model/settings were not tuned on this collection.

Model SHA-256: `744d6078dd2211e0e271e2a21042df4b95218a74ea78bc33a64c33057dfb2da3`.

## Results (32 scored photographs)

| Method | Count MAE (grains) | Broken-percentage MAE (percentage points) |
|---|---:|---:|
| Aspect-ratio baseline | 477.8125 | 39.4434 |
| Decision Tree | 477.8125 | 49.9581 |

| Condition | Labeled photos | Tree count MAE | Tree percentage-point MAE |
|---|---:|---:|---:|
| Separated | 12 | 545.50 | 64.8696 |
| Lighting/background | 10 | 485.60 | 47.1029 |
| Overlap | 10 | 388.80 | 34.9194 |

**Neither local proposal target is met** (count MAE <= 5, percentage-point MAE <= 5). The baseline has lower percentage error here. Identical total count error reflects the shared detector. Two tree cases are within 5 grains; none is within 5 percentage points. No scored image had zero detections and no execution failed. First-image-excluded mean working-image decode + tree pipeline time was 7,550.56 ms/image on this run, excluding original resizing/rendering/output writing.

Outputs show substantial non-grain regions on textured backgrounds. Aggregated counts do not identify each false box or missed grain. They cannot establish per-grain F1, a classification confusion matrix, detection precision/recall, mAP or mask IoU.

## Evidence and reproduction

```
python src/import_local_photos.py --archive "path/to/Bigas Check Local Photos.zip"
python src/evaluate_local.py --output outputs/local_reproduction
```

The default first-run output refuses overwriting. Retained evidence: `outputs/local_20261120_frozen/{protocol.json,metrics.json,per_photo_results.csv,progress.json}`, per-image annotation/mask/results JSON, plus `data/local_20261120/{manifest.csv,audit.json,photo_contact_sheet.jpg,working_1600}`.

The four-page `Local_Evaluation_Report.pdf` and Phase 3/4/5 addenda supplement the packages prepared on 19 November. They supersede earlier statements that no local count references existed. The original reports and dates are preserved. Source originals remain local and excluded from broad git adds; local photos do not inherit the Kaggle MIT license.

After these images guide improvements they become development evidence. Obtain new physical samples/sessions for an untouched final test, and record reused piles/session membership when possible. Confirm the missing counts, the whole-only filename convention, and conduct a second human review before final claims.
