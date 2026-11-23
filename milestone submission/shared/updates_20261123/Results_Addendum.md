Pipeline and evaluation protocol

Input/optional crop -> EXIF/RGB and max-edge resize -> adaptive foreground -> morphology/touching-region separation -> border/shape/area checks -> silhouette features -> pooled tree or existing multi-grain count calibration -> labels/counts/mask/annotated output. src/predict.py and src/run.py provide one-command image or folder processing.

The normal dark detector could reject dim grains as glare. When sparse accepted regions and predominantly low-contrast rejections indicate this case, texture recovery searches smooth cream-coloured foreground relative to patterned fabric. Expected counts and filenames never determine the result. Weights and dataset assignments are unchanged.

All 33 Local Dataset 1 photographs and 17 Local Dataset 2 training photographs were processed before/after, max-edge 1600, min area 30, auto/adaptive, touching split enabled. Exactly one photo changed its predictions. One Local Dataset 1 photo has no count reference. Full CSV and code/model hashes accompany this report.

Every image was previously inspected, used for training, or exposed in development. This is a regression/development comparison, not the untouched representative set required for Phase 3 or final evaluation. Count labels do not identify the true class of each detected region.

---

Patterned background recovery

local_010: 4 candidates before, 12 after at default area 30. Each recovered centroid matches one of 12 reviewed grain locations with no extra detections in that positional check. Reference: 8 whole / 4 broken. Current prediction: 9 / 3; classification remains incorrect.

Blue cloth still finds 10 grains but labels 6/4 vs 5/5. Green cloth finds 18 but labels 17/1 vs 18/0. No total or class predictions changed on the other 49 local photographs.

---

Current development measurements

Main: count MAE 3.00 grains, percentage MAE 2.92 points. Aspect baseline on the same detections: count MAE 3.00, percentage MAE 4.18. Main core processing mean 1204 ms/image after three warm-ups, excluding decoding/rendering/HTTP. Values before and after are unchanged on these ten images.

All labelled Local Dataset 1 images (32): count MAE 3.59 -> 3.34; percentage MAE 11.69 -> 10.65 points. Uncropped Local Dataset 2 training photos (17): count MAE 29.24 and percentage MAE 40.26, unchanged. Background false detections remain severe there.

Validation: tree accuracy 95.70%, macro-F1 0.9369; baseline accuracy 97.25%. Reused source test: tree accuracy 96.22%, macro-F1 0.9430; baseline accuracy 95.88%. There are 22 current test-tree failures, grouped by hypothesised silhouette confusion, with matrices and an error contact sheet.

On ten source images: 44.87 ms validation / 42.14 ms test mean including image loading, after three warm-ups. Source images are much smaller than local photos. These timings and local core-only timings have different scopes and must not be compared as an algorithm speedup. Tree F1 is not multi-grain detector precision or mask IoU.

---

Errors, improvements and readiness

Textured backgrounds: improve region rejection and crop guidance with training/validation examples; expected result is fewer false grain candidates on original Local Dataset 2 photographs.

Whole/broken ambiguity: collect reviewed local grain-level labels across rice varieties and audit segmentation before supervised refitting; expected result is fewer short-whole/elongated-broken confusions. Count totals alone are insufficient.

Dim/touching/occluded grains: label grain locations or masks on training/validation hard cases and assess splitting/recovery errors; expected result is fewer merged/missed/split grains. Validate once on newly held-out captures after freezing changes.

51 project tests pass. Isolated new venv / export: 47 pass, 4 missing-private-data skips; model/gallery analysis works without raw data. Live checks cover 62 gallery asset routes and equivalent sample/upload results. Current twelve-case demo remains 9 pass / 3 fail.

Not all checkpoints are complete. Current evidence supports running software and development comparisons. Required untouched representative evaluation, current main report/slides, actual contributions, updated demo/rehearsal and checkpoint/release tags remain pending. Earlier PDFs/ZIPs/videos are historical; use the current audit for requirement-by-requirement status.
