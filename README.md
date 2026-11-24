# BigasCheck

**Review and quality update (24 November 2026):** After analysis, open **Review and correct grains** to merge fragments, split merged regions by tracing each grain, add misses, remove false detections and correct labels. Automatic predictions stay separate from reviewed counts. Visual-quality review now includes discoloration and impurities; those fields remain **not assessed** automatically until suitable labelled data and a validated model exist. Download/resume reviews, corrected overlays, and reviewed training outlines. See [visual quality](docs/VISUAL_QUALITY.md) and [annotation/training workflow](docs/INSTANCE_TRAINING.md). No new instance/defect model has been trained yet.

An initial local computer vision prototype following the supplied Week 11 proposal: segment rice grain regions, measure geometric/color features, compare a geometric baseline with a Decision Tree, and estimate broken grains **by count**.

**Application update (23 November 2026):** The sample picker now ships with **27 Kaggle items and 4 Local Dataset 2 training crops**, with no Local Dataset 1 entries. Patterned-cloth recovery finds all 12 reviewed grains; whole/broken remains 9/3 against the 8/4 reference. Current software tests: 51 pass; an isolated fresh install and portable export also passed (47 tests plus 4 private-data skips). See [current changes and measured limits](docs/REQUESTED_UPDATES_20261123.md) and [milestone audit](docs/MILESTONE_CHECKLIST.md). The milestones still have pending hand-in requirements.

## Team

Zyril Dela Paz · Axcel Andrei Delos Reyes · Jhed Aeron Lachano.

Individual contributions are deferred. See `docs/TEAM.md`. The Kaggle dataset page lists MIT and links to the notice preserved with its original attribution in `docs/USER_PROVIDED_LICENSE.txt`. Source verification is recorded in `THIRD_PARTY_NOTICES.md`.

## Repository quick start

```powershell
git clone https://github.com/HotokeZ/CSST-106.git
cd CSST-106
.\setup.ps1
.\start.ps1
```

The repository includes the small trained CPU model and the extracted feature/split table. Raw dataset images and personal uploads are excluded. You can upload your own photo immediately after setup.

The curated sample picker is included in a fresh clone. To rebuild the full Kaggle partitions for source-image benchmarks, download the original Kaggle ZIP, save it as `inputs/archive.zip`, then run:

```powershell
python -m bigascheck extract inputs/archive.zip data/raw
python -m bigascheck prepare-samples
```

Use `.venv\Scripts\python.exe` instead of `python` for these commands when using the environment created by `setup.ps1`. No retraining is needed to rebuild the gallery from the published split table. Full image-based benchmarks and failure pictures also need these source images; the raw dataset is not bundled.

Local evaluation collection: start with 30 labeled photos, ideally plus 10 new untouched final captures. See `docs/LOCAL_PHOTO_COLLECTION.md` for conditions, counts and group IDs.

## Run the interface now

From this Bigas Check folder:

```powershell
python app.py
```

Open http://127.0.0.1:5000. You can upload a photograph and inspect detected regions immediately with the libraries available here. Without a real trained model, the interface explicitly shows **unclassified** grains and withholds the broken percentage.

The upload box previews the original selected image immediately. Click it again or drop another image to replace the photo; the file picker remains available over the preview. Dataset samples also appear in this box. Replacing or clearing an image releases its browser preview URL and clears results from the previous photo. Selecting a new image while an analysis is running prevents the previous response from replacing the new photo's results.

## Try a dataset sample

The **Or try a test sample** gallery lets users analyze a photo without uploading a file. Filter by Whole, Broken or Mixed, and by Kaggle or Local Dataset 2. Reference labels/counts appear separately from predictions. Uploading a file clears the selected sample. Local Dataset 2 cards explicitly identify training demonstrations.

The original Kaggle assignments remain 2,713 training, 582 validation and 582 reused development-test grains. The default curated picker contains 24 original test grains, three declared six-grain composites made from those grains, and four reviewed Local Dataset 2 training crops. There are no Local Dataset 1 gallery entries. Composites are software demonstrations, not captured multi-grain photographs.

The separated image folders and per-split CSVs are under `data/splits/<dataset-version>/train`, `validation` and `test`. A versioned catalog prevents an old gallery from silently being reused after training assignments change. Exact hashes are checked against the saved feature table, and known capture groups must not cross partitions. The original public dataset still lacks verified capture-session IDs; the split remains exploratory at image level.

To rebuild full Kaggle split folders and thumbnails, use `python -m bigascheck prepare-samples`. To rebuild the default curated picker after acquiring the source images and reviewed Local Dataset 2 inputs, use:

```powershell
python src/prepare_gallery.py
```

`train.ps1` still prepares the full source partitions. Run `python src/prepare_gallery.py` separately to rebuild the curated picker. The existing curated assets work without raw data. These demonstrated images are exposed development/training material; use new independently held-out local captures for final evaluation.

For a clean environment with all proposed dependencies, run:

```powershell
.\setup.ps1
.\start.ps1
```

Setup requires internet access. The pinned Python 3.13 CPU/SciPy environment was installed in a new isolated venv on 23 November 2026; the exported app/model/gallery and software tests ran with user site disabled and raw/private datasets absent. This verifies the same Windows laptop, not a second machine. OpenCV is optional and excluded from the default environment because changing the backend requires compatible training and evaluation.

## Real dataset workflow

Dataset source: https://www.kaggle.com/datasets/cristhiansempertegui/dataset-de-arroz-peruano

The supplied ZIP was found at `inputs/archive.zip` and extracted to `data/raw`. Its documentation identifies `entero` as whole and `quebrado` as broken. The initial source-label workflow excludes stained/chalky classes, removes exact duplicates, and excludes images with contradictory labels. See [docs/DATASET.md](docs/DATASET.md) for provenance and evaluation limits.

To train the initial classifier and save the model used by the app:

```powershell
.\train.ps1
# Or supply a different ZIP location on the first import:
.\train.ps1 -Archive 'C:\path\to\archive.zip'
```

Restart `python app.py` after training. This source-label mode uses an explicitly exploratory image-level split because original capture-session IDs are absent. It does not claim session-independent evaluation or independent manual verification. The stricter reviewed/grouped workflow remains available below.

```powershell
python -m bigascheck audit inputs/archive.zip --output outputs/dataset_audit.json
python -m bigascheck extract inputs/archive.zip data/raw
python -m bigascheck manifest data/raw data/manifest.csv
# Fill reviewed labels, original capture groups and verified=true in manifest.csv.
python -m bigascheck train data/manifest.csv --output artifacts
python -m bigascheck analyze path/to/sample.jpg --model artifacts/model.joblib
python -m bigascheck evaluate-samples data/samples.csv --model artifacts/model.joblib
```

Training uses isolated labeled grain images. It stops if a training image yields anything other than one accepted grain region. It extracts area, equivalent-ellipse major/minor axes, aspect ratio, solidity, extent, RGB means and standard deviations. All dimensions are pixels. Group splits prevent original sessions from crossing partitions when correct groups are provided. Identical image files are rejected.

Artifacts: `model.joblib`, `evaluation.json`, `features_and_splits.csv`. CLI analysis exports `annotated.png`, `mask.png`, `results.json`, `grains.csv`. The interface downloads these results in memory without retaining uploaded photographs. Only load trusted locally generated model files; joblib is a pickle format.

Restart the server after training so it loads `artifacts/model.joblib`. To select another trusted model:

```powershell
$env:BIGASCHECK_MODEL = 'artifacts/my_model/model.joblib'
python app.py
```

## Software checks

The checkpoint review and remaining requirements are in `docs/MILESTONE_CHECKLIST.md`. Use these commands to reproduce evidence without retraining:

```powershell
python src/predict.py --input inputs/rice_test_2.jpg --output outputs/prediction
python src/run.py --input path/to/image_folder --output outputs/batch
python src/evaluate.py --split validation --output outputs/checkpoints/validation
python src/evaluate.py --split test --output outputs/checkpoints/development_test
python src/test_cases.py
```

The evaluator writes per-class precision/recall/F1, macro-F1, baseline/tree confusion matrices, weights/data hashes, a failure gallery, preprocessing evidence and CPU timing after three warm-ups. It measures classification from saved per-grain features; speed separately runs the image pipeline. Multi-grain inference also uses count calibration, so tree F1 is not full-pipeline counting accuracy. Current twelve-case demo results are 9 pass / 3 fail. See the dated update for current full-photo count/percentage errors.

The UI exposes core processing milliseconds and per-grain Decision Tree leaf votes. Leaf votes are not calibrated certainty. There is no fabricated probability for the geometric baseline.

Current milestone PDFs and slide PDFs exist, but the main report and slides contain older methods/results and require revision. Independent final evaluation, actual release tags, updated demo/rehearsal and truthful member contributions are still pending. Read [the current requirement-by-requirement audit](docs/MILESTONE_CHECKLIST.md).

```powershell
python -m unittest discover -s tests -v
```

An artificial dataset and sample are included as reproducible software smoke tests:

```powershell
python -m bigascheck demo
python -m bigascheck train data/demo/manifest.csv --output artifacts/synthetic_smoke_test
python -m bigascheck analyze data/demo/sample.png --model artifacts/synthetic_smoke_test/model.joblib --output outputs/synthetic_smoke_test
```

These images are drawn ellipses, **not rice training data**. Their results are not research findings. The default interface does not automatically load the artificial model.

## Scope and remaining work

Implemented: dataset audit/import tools, reviewed-label manifests, segmentation, features, baseline and tree training, grouped validation/testing, per-grain and multi-grain evaluation, annotated results, CSV/JSON downloads, and local upload interface.

Remaining: collect independent capture-grouped final photos and manual ground truth, improve remaining background/classification errors, and evaluate the proposal goals on that frozen set. Dataset MIT attribution is preserved; user photos have separate provenance. Existing local development scores and source classifier F1 do not establish independent final-photo performance.

The upload interface defaults to automatic background detection and distance-transform watershed separation of touching grains. Pale-background mode uses local contrast to detect white rice on a light surface. Background and minimum-area controls remain available with a loaded classifier. Connected-region mode is also available for inspecting the effect of separation. Touching or overlapping grains can still merge or split incorrectly; results need manual verification.

The current default model uses dimensionless silhouette features: aspect ratio, solidity and area divided by major/minor-axis product. These features do not depend on uniform camera scale or RGB background color, so this model can return experimental whole/broken predictions on pale-background images. Incorrect segmentation, overlapping grains and naturally short whole grains still affect the predictions. The interface labels these as experimental predictions; its percentage is not a validated rice quality measurement.

The earlier pixel model is preserved as `artifacts/pixel_model.joblib`. When explicitly loading that older model, background/scale mismatches still withhold classification. No physical calibration, optional visible-defect classifier, or official rice grading is implemented. The development server binds to localhost and is intended for a local student demonstration.

To refit the shape classifier from the previously extracted features without processing all source PNGs again:

```powershell
python -m bigascheck train-shape
```

`train.ps1` now trains the original feature pipeline and then saves the shape classifier as the default `artifacts/model.joblib`. The source table's train/validation/test assignments are retained. The reused development test set is not a substitute for a fresh held-out local-photo evaluation.

For command-line pale-background detection:

```powershell
python -m bigascheck analyze sample.jpg --model artifacts/model.joblib --background auto --split-touching
```

## Technical references

- OpenCV contour features: https://docs.opencv.org/4.x/dd/d49/tutorial_py_contour_features.html
- scikit-learn Decision Trees: https://scikit-learn.org/stable/modules/tree.html
- scikit-learn group splitting: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupShuffleSplit.html
