# New local single-grain training update — 20 November 2026

Imported `Bigas Check Local 2.zip`: **17 unique photos, 8 labelled whole and 9 labelled broken**. All are training-only. Original photo bytes, user folder labels and archive/image SHA-256 hashes are preserved under `data/local_grains/batch_20261120_2`.

The local collection now has **35 training photos, 10 development-test photos and 5 sample/demo photos**. The 35 training photos consist of the previous 18 multi-grain photos plus these 17 single-grain photos. One of the original 18 still lacks reference counts, leaving 34 training photos with usable supervision. The original 33-photo partition files and memberships were preserved, rather than rewritten.

## Data review

The automatic detector produced additional background candidates in these new full photos. Only the visible, complete intended grain was selected and visually reviewed in each image. The remaining candidates received no whole/broken labels. Review decisions, selected candidate IDs, masks, crops and extracted features are preserved in `artifacts/local_single_extraction_v1`.

The supplied whole/broken folder label is the classification reference. The visual review establishes target identity and crop completeness; it does not independently measure physical breakage. Capture/session and rice-sample IDs remain unknown and blank. No new image duplicates an original Kaggle or local partition image by SHA-256. Related captures can still exist despite differing hashes.

## Training

The supervised shape tree is refitted on **2,713 Kaggle training grains plus 17 local single-grain targets = 2,730 labelled grains**. It uses aspect ratio, solidity and ellipse fill. Class weights are balanced within each source domain; local domain weights 0.1, 0.25 and 0.5 are considered, so the small local collection is not simply overwhelmed by the Kaggle collection.

Tree selection uses 75% Kaggle validation macro F1 plus 25% leave-one-photo-out macro F1 within the new local training photos. The chosen tree has depth 3, minimum leaf size 3 and local domain weight 0.5. Leave-one-photo-out selection scores can be optimistic because capture/sample identities are unknown. The final tree is fitted on every training grain.

The supplemental multi-grain threshold is then refitted using the Kaggle training labels, all 17 new local single-grain labels, and the original 17 labelled training-photo count references. Labelled source-domain errors are balanced between Kaggle and local single grains. Test and sample labels do not enter fitting. The original source baseline is retained. The new run is `artifacts/combined_count_v3`; the supervised tree report is `artifacts/combined_single_v2/report.json`.

## Results and limits

On the same 10-photo **development-test** partition, broken-percentage MAE changed from **11.92 to 8.58 percentage points** versus the previously installed combined model. Detection count MAE remains **7.20 grains**, because detection was not changed. All photos were already inspected during development, so this is not independent final evaluation.

The new supervised tree scores 96.22% accuracy and 0.910 broken F1 on the existing Kaggle development-test features. This isolated-grain classification result must not be presented as local multi-grain counting accuracy. All 17 new selected training targets are classified correctly after fitting; that is training resubstitution, not a test accuracy claim.

Some individual predictions regress. The 12-whole/10-broken training photo still has 22 detections, but the updated combined rule predicts **14 whole / 8 broken**. The green 18-whole photo predicts 17 whole / 1 broken, and the blue 5-whole/5-broken photo predicts 6 whole / 4 broken. More local labels help the measured average without resolving every case. Background false detections in new full single-grain photos still need detector work; the reviewed training crops exclude them.

## Reproduce

For the existing imported batch and reviewed features:

```powershell
python src/train_single_grains.py --output artifacts/single_reproduction
python src/train_local.py --weights artifacts/single_reproduction/model.joblib --local-single-features artifacts/local_single_extraction_v1/reviewed_features.csv --output artifacts/count_reproduction
```

These commands create a candidate run and do not replace the active model. Choose new output paths for every run; existing run evidence is not overwritten.

For a new batch, use the importer and extractor, then inspect the candidate crops and fill `review.csv` with the correct `reviewed_grain_id` and `reviewed=true` for each image before exporting features:

```powershell
python src/import_single_grains.py "path/to/new_photos.zip" --output data/local_grains/new_batch
python src/extract_single_grains.py --manifest data/local_grains/new_batch/manifest.csv --output artifacts/new_extraction
# Inspect candidates, masks and crops; fill artifacts/new_extraction/review.csv.
python src/export_reviewed_grains.py --extraction artifacts/new_extraction --manifest data/local_grains/new_batch/manifest.csv --output artifacts/new_extraction/reviewed_features.csv
python src/train_single_grains.py --local-manifest data/local_grains/new_batch/manifest.csv --local-features artifacts/new_extraction/reviewed_features.csv --output artifacts/new_supervised_run
```

Keep the existing 10 test and 5 demo images, and their crops, out of these training folders. Collect a separate fresh set with known capture/sample groups for final evaluation.
