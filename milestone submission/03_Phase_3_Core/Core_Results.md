Phase 3 | integrated method

python src/run.py --input sample_inputs --output outputs/demo --background dark --connected-regions

RGB input -> foreground thresholding -> morphology/filtering -> optional watershed -> shape features -> Decision Tree -> annotated image, binary mask, JSON and grain CSV. src/run.py delegates to bigascheck/runner.py; bigascheck/vision.py and model.py implement the core.

The main classifier is a depth-5 Decision Tree with minimum leaf size 10. It uses aspect ratio, solidity and ellipse fill. The baseline thresholds aspect ratio. Training/validation/test assignments are preserved; no training images were moved into the test gallery.

The 582 development-test images were excluded from training, but have since been exposed for demos/development. The 12 fixtures are software checks. Neither qualifies as a new set never used for training or tuning. Fresh lighting, blur, angle, occlusion and clutter photographs remain necessary.

---

Phase 3 | preliminary measurements

All rows measure isolated-grain classification from the saved extracted feature table. Baseline is stronger on validation; a small tree advantage on development test does not establish general superiority.

Current run: validation mean 46.03 ms/image; development-test mean 46.05 ms/image. Each uses 3 warm-ups and 20 measured images, model loaded once. Image loading, segmentation, extraction and classification are included; rendering/web/output writing are excluded.

python src/evaluate.py --split validation --output outputs/validation
python src/evaluate.py --split test --output outputs/development_test. Exact hashes, dependencies and hardware are in shared/evaluation/*/metrics.json. Runtime depends on laptop load.

Split / method | Accuracy | Macro-F1 | Broken F1

Validation / Baseline | 0.9725 | 0.9580 | 0.9333

Validation / Decision Tree | 0.9588 | 0.9389 | 0.9040

Development test / Baseline | 0.9588 | 0.9362 | 0.8983

Development test / Decision Tree | 0.9605 | 0.9409 | 0.9069

---

Phase 3 | failure analysis

16 whole references were predicted broken; 7 broken references were predicted whole. Short/low-elongation whole silhouettes and elongated broken look-alikes are hypotheses, not independently verified causes. Review source labels and contours before changing the model.

The grouped gallery on the following page contains at least 10 actual errors, and all 23 are copied under shared/evaluation/development_test/failures. The CSV/JSON logs identify references, predictions and source files.

---

Phase 3 | failures and improvement plan

1. Review short-whole / long-broken errors and add verified hard development examples; expected result: fewer false broken labels without reducing broken recall. Confirm using validation F1.

2. Collect contrast/lighting fixtures and improve pale-background segmentation; expected result: lower false region count and count MAE on local development photos.

3. Add manually labeled touching/overlapping grains and refine watershed markers; expected result: fewer merges/splits, checked with count MAE and reviewed masks. Targets are plans, not achieved results.
