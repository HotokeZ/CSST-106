# Dataset preparation

Supplied source: https://www.kaggle.com/datasets/cristhiansempertegui/dataset-de-arroz-peruano

The user supplied `archive.zip` and `BigasCheck_Week11_Project_Proposal.docx`. The proposal was read. The archive was subsequently found in `inputs/archive.zip` and extracted to `data/raw`.

The archive has 6,599 categorized PNGs: 3,352 `entero` (whole), 867 `quebrado` (broken), 857 `mancha` (stained), and 1,523 `tiza` (chalky), plus four viewer images. The included `Readme.md` confirms these category meanings and describes capture during August–September 2023. Sample images were visually inspected; the four integrity/defect classes are isolated grains on black backgrounds. No original capture-session identifiers or explicit redistribution license were found in the archive README.

## Initial source-label trainer

Run `.\train.ps1` to prepare and train the initial model. It uses only whole/broken folders and keeps `verified=false`, `label_source=dataset_folder`, and unknown capture groups blank. Exact duplicates are removed; identical images appearing under contradictory labels are excluded from both classes. `data/peruvian_source.import.json` records these exclusions. Images that do not yield exactly one accepted grain are excluded and listed in `artifacts/excluded_images.csv`.

The explicit `--source-labels` mode uses a stratified image-level 70/15/15 split. It records `training_mode=exploratory_source_labels` and `split_unit=image`. These scores are exploratory: related source photographs may cross splits, and the labels have not received independent per-image manual review. The default trainer still requires reviewed labels and known capture groups for the research workflow. A maximum component fraction of 0.6 is used because isolated source grains may occupy more than 15% of their crops.

```powershell
python -m bigascheck prepare-peruvian data/raw data/peruvian_source.csv
python -m bigascheck train data/peruvian_source.csv --source-labels --max-area-fraction 0.6 --output artifacts
```

### Initial run

The real-data model is saved at `artifacts/model.joblib`. Import left 3,879 unique, nonconflicting source images; training excluded two further images and used 3,877 grains (3,087 whole, 790 broken). The split contains 2,713 training, 582 validation and 582 test images. The selected Decision Tree has depth 3 and reports test accuracy 0.9622 and broken F1 0.9106. The geometric baseline reports accuracy 0.9708 and broken F1 0.9264. Neither model was selected or retuned based on those test results.

These are exploratory image-level source-dataset scores, not independent capture-session or local-photo results. In particular, the fitted tree relies heavily on pixel length; camera-scale matching is essential. All details and confusion matrices are in `artifacts/evaluation.json`.

### Shape classifier update

The initial pixel model is preserved as `artifacts/pixel_model.joblib`, with its report in `artifacts/pixel_evaluation.json`. The default `model.joblib` now uses dimensionless aspect ratio, solidity and ellipse-fill features. It was refitted from the existing source feature table with the original split assignments. `artifacts/evaluation.json` is the current shape-model report. This version returned development test accuracy 0.9605 and broken F1 0.9069, but the test set has now been used across prototype development rounds; final validation needs fresh independently held-out local samples.

The original local `rice test 2.jpg` was used for segmentation regression checks, not for training integrity labels. The previous mask returned 13 regions. Replacing global hole filling with small-hole filling, separating shadow/table/rice intensity classes, and improving watershed flooding returned 131 accepted candidate regions. This is a detection-output count, not verified ground truth. Classification on this crowded photograph is explicitly experimental; many overlaps and naturally short whole grains may be labeled incorrectly. No local-photo accuracy or broken-percentage accuracy is claimed.

## Import the archive

Place the downloaded archive at `inputs/archive.zip` in the project folder, then run:

```powershell
python -m bigascheck audit inputs/archive.zip --output outputs/dataset_audit.json
python -m bigascheck extract inputs/archive.zip data/raw
python -m bigascheck manifest data/raw data/manifest.csv
```

The audit lists image counts by folder, metadata files and example paths without assuming folder names are valid labels. Extraction rejects path traversal, symlinks and existing output files. The manifest generator deliberately leaves labels and group identifiers blank.

## Label and group rules

- One manifest row = one isolated, individually labeled grain image.
- `image`: path relative to the manifest CSV.
- `label`: `whole` or `broken`, based on manual review and a consistent written annotation guide.
- `group_id`: original photograph, sample or capture-session identifier. All crops/augmentations from the same capture belong to the same group. Use the broadest shared session identifier where known.
- `verified`: `true` only after label and group review. Two reviewers should resolve disagreements as proposed.
- Require at least seven independent groups; more are preferable for meaningful held-out evaluation. Both classes must be present in each split.

Do not treat rice variety names as whole/broken labels. Stained/chalky categories describe defects, which may coexist with either integrity class; they need independent integrity annotations. Do not silently map either category to broken or whole. If images contain several grains, annotate/crop each grain first; all crops keep their original group. Current training deliberately rejects images in which segmentation finds zero or multiple components.

Confirm the dataset's original provenance and usage/license terms on Kaggle before redistribution. Keep its metadata alongside the raw files. If original capture groups are unknown, record this limitation and obtain reliable grouping before claiming leakage-free research results. An arbitrary unique group for every crop is not reliable grouping.

## Capture conditions

Use a matte contrasting background and even illumination. Keep grains separated. Keep image resolution, camera distance, and preprocessing consistent between training and inference: pixel features change with scale. Switching from small tightly cropped dataset images to high-resolution multi-grain photographs may invalidate predictions without scale calibration. Avoid crops that touch the image edge; pad them with the same background if necessary. Inspect masks before training. Set `--max-area-fraction` higher only when a valid isolated grain occupies more than the default 15% of its image.

The interface now provides optional distance-transform watershed separation and automatic/pale-background segmentation. Training still uses the original connected-component settings unless explicitly changed. Watershed cannot recover invisible boundaries in heavily overlapping grains. Millimeter calibration and optional chalkiness/discoloration classification are not implemented. Excluded noise, large components and border components reduce the reported count. A count comparison alone cannot establish instance-localization precision/recall.

## Evaluation

### On-disk partitions and sample gallery

`python -m bigascheck prepare-samples` copies the exact saved split assignments into versioned train/validation/test folders under `data/splits`. Counts are 2,713 training (2,161 whole, 552 broken), 582 validation (463 whole, 119 broken), and 582 test (463 whole, 119 broken). The model and its assignments are preserved; the exporter does not reshuffle data.

The public application gallery indexes only test images. Three additional gallery cards are composites of six test grains each: all whole, all broken, and mixed. The source hashes for every composite are recorded in the catalog, and none comes from training or validation. Reference labels are metadata for comparison after selecting a sample; they are not passed to the prediction function. The API cannot select arbitrary training file paths.

The export includes original image copies, CSV manifests, thumbnails, and `data/splits/catalog.json`. Retraining automatically rebuilds the gallery. If the feature-table fingerprint changes before rebuilding, the application refuses the stale gallery. Prior versions are retained in separate folders.

Interactive test-gallery use is a demonstration, not a new accuracy study. It does not resolve unknown original capture groups, and repeated tuning based on these visible samples would contaminate their role as a final evaluation set.

The pipeline makes approximately 70/15/15 splits by group, with actual counts depending on group sizes. Validation selects the length threshold and tree parameters. The saved model remains fitted on the training split; held-out test results are written once per training run. Repeated manual tuning based on test scores would contaminate that test set.

`evaluation.json` records per-grain classification results and confusion matrices for both methods. `features_and_splits.csv` records exact groups, file SHA-256 hashes, features and assignments. Exact duplicate files are rejected; visually similar or reencoded duplicates require manual audit.

For separate held-out multi-grain photos, fill `data/samples.example.csv` with manual whole/broken counts. Use groups absent from training and validation. Run `evaluate-samples` to measure count MAE and broken-percentage MAE in percentage points. If any photograph has zero detections, the overall percentage MAE is withheld rather than silently dropping that photograph. Report public-data and local-data evaluations separately.
