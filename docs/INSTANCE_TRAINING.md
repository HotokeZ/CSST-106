# Grain review and instance-training workflow

This adds a manual correction and annotation workflow. It does **not** claim that automatic oversplitting/merging is solved or that a rice instance model has been trained. The existing detector and trained classifier remain the automatic baseline.

## Correct an inspection

1. Upload or select a photo and analyze it. Open **Review and correct grains** below the results.
2. Select grain IDs in the list (Ctrl/Cmd selects multiple). Blue outlines show the selection. The initial rectangles are automatic proposals, not segmentation masks.
3. For an over-split grain, select its fragments, choose **Merge selected fragments**, click around the actual single grain, **Finish outline**, then **Apply correction**.
4. For a merged region, select its ID and choose **Split one merged region**. Trace each real grain separately, pressing **Finish outline** after each. Apply after at least two outlines. Change child labels afterward if needed.
5. Use **Add missed grain**, **Remove false detections**, **Change selected labels**, and **Trace / replace one grain** for other errors. Add requires an empty selection. Use Ctrl/Cmd-click to deselect an ID.
6. **Undo point**, **Clear drawing**, **Undo correction**, and **Reset review** are available. A new analysis or a changed source/crop resets the review. Download the corrected report before leaving; it can be restored using **Resume a saved review** after analyzing the same image/crop. The image bytes must match.
7. **Download corrected report** includes the unchanged automatic result, manual objects, edit history, corrected summary, processed image and coordinate metadata. **Download corrected image** saves the current review overlay. The original report/CSV/image buttons still export automatic results.

Corrected counts are human review, not improved model predictions or new automatic accuracy measurements. Newly drawn polygons carry their explicit class label, not a fabricated model confidence or inherited geometric measurements. Unknown labels withhold the corrected percentage.

## Create usable grain-level labels

For each image, trace every visible grain and impurity outline, including detections that were already correct; remove false detections and add misses. Use **whole**, **broken** or **impurity** only where known. For rice, explicitly mark **No visible discoloration** or **Discolored**. Shadows and warm lighting are not proof of discoloration. Folder labels/photo totals do not identify every grain in a mixed photo. Ambiguous/occluded examples need consistent labelling guidance; do not guess hidden boundaries from totals.

Open **Prepare training annotations**, enter a real capture group, choose the partition and confirm all outlines/labels were reviewed. Related views, bursts and crops of the same physical sample/session must share a group and partition. The export refuses automatic rectangles, unclassified objects or unassessed rice discoloration. Confirmation is a user assertion, not an independent audit. Training labels preserve both integrity and discoloration: `whole`, `broken`, `discolored_whole`, `discolored_broken`, `impurity`.

Download the labelled outlines/image. This is a LabelMe-style JSON with pixel polygons and its processed RGB image embedded. Keep each photo's JSON under a distinct filename, in `inputs/instance_annotations/`. Coordinates belong to the embedded processed image/crop; do not pair them with the original full-resolution camera file. The export preserves original crop metadata.

Start with representative separated, touching, crowded, dim, shadowed and textured-background examples. Include short whole grains, long broken fragments, genuinely discolored rice, and visible foreign objects. Keep training/validation groups separate; all configured classes need examples in each. Keep new final-test captures untouched until the pipeline is frozen. Existing gallery/regression photos have been exposed during development and cannot become an independent final test merely by changing their partition.

## Prepare a dataset

Use the normal application environment:

```powershell
.venv\Scripts\python.exe src/prepare_instances.py --annotations inputs/instance_annotations --output data/instances_v1
```

The converter validates reviewed polygons, image dimensions, finite/bounded coordinates, polygon intersections, duplicate decoded images and capture-group overlap. It writes a new dataset with YOLO segmentation labels, generated safe image names, `dataset.yaml` and a provenance/count manifest. It refuses to overwrite a nonempty output. Review checks cannot prove that a user's classes or group IDs are correct.

## Train the optional model after labels exist

Ultralytics documents segmentation training and per-object masks at https://docs.ultralytics.com/tasks/segment/ and the polygon data format at https://docs.ultralytics.com/datasets/segment/. The starter uses a small pretrained `yolo11n-seg.pt`; its generic pretrained categories are not a trained rice detector.

Use a **separate** training environment, because Ultralytics installs PyTorch/OpenCV and installing those in the application environment would change its tested SciPy backend. This optional environment has not been installed or training-validated in this change. Select compatible pinned package versions on the training machine and save its requirements with the run. Ultralytics code/weights have their own licence terms; they do not inherit the Kaggle dataset's MIT notice.

```powershell
python -m venv .venv-instances
.venv-instances\Scripts\python.exe -m pip install ultralytics
.venv-instances\Scripts\python.exe src/train_instances.py --dataset data/instances_v1 --output outputs/instance_training_v1 --device cpu --epochs 100 --batch 2
.venv-instances\Scripts\python.exe -m pip freeze > outputs/instance_training_v1/requirements-training.txt
```

The starter requires reviewed training and validation data with all five classes before it loads a model. It preserves the app's current weights. It defaults to CPU, batch 2 and zero loader workers for a portable Windows starting point; training time and memory need measurement. Model weights may download on first use.

## Evaluation and integration gate

Before promoting new weights into the app, compare them with the automatic baseline on the same fixed development images. Record missed/false grains, split events, merge events, whole/broken errors, count MAE and CPU speed. Count agreement alone can conceal a miss and a false positive cancelling out. With independently reviewed instance masks, also report mask precision/recall and mask mAP/IoU using a one-to-one matching protocol. Fix the match threshold/protocol before final scoring.

Train/refine only with training/validation data. Freeze weights/settings, then evaluate new group-separated final captures. The current application does not silently load optional instance-model weights: integration and any claimed accuracy improvement remain pending actual training and evaluation. Manual corrected outputs must stay separate from automatic results in milestone reports.

## Software checks

```powershell
python -m unittest discover -s tests -v
node --test tests/review-core.test.cjs
```

These validate edit bookkeeping, polygon/data integrity, split leakage and existing regressions; they do not establish model quality. Annotation/correction data is downloaded on demand and not stored by the web server. Raw annotation collections and prepared datasets should remain outside Git; source/tools/tests are published.
