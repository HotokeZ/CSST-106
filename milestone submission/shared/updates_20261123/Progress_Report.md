Progress against the proposal

Estimated implementation completion: 80% (engineering estimate, not a rubric mark). Import/split tools, shared preprocessing/features, baseline and trained model, image CLI, upload preview/crop, Kaggle-first gallery and result downloads run. Remaining effort centres on detector/classification errors, independent evaluation and final documentation. Hand-in completeness is lower than implementation progress.

Pinned environment installed in a new isolated venv; current model and curated gallery ran without raw data. Current project: 51 tests pass; export: 47 pass, 4 private-data skips.

Kaggle partitions and current data card, validation results, 12-case demo log, six historical input/output examples and current failure galleries are available.

The patterned Local Dataset 1 photo now has 12 spatially checked detections. Current gallery is 27 Kaggle / 4 Local Dataset 2; no Local Dataset 1 samples.

The supplied brief schedules core implementation before final testing and presentation. This review records current evidence on 23 November, not work claimed at an earlier class checkpoint. Existing reports/slides are historical drafts and the release tags are absent.

---

Pending work and revised plan

An independent final capture set is absent. Existing Kaggle/local test photos were exposed during development; unknown physical sample groups limit independence.

Pattern classification remains 9 whole / 3 broken vs 8/4. Full-frame Local Dataset 2 images have substantial fabric false detections; cropped training demos do not resolve that.

Report/slide content, real contributions, current demo recording/rehearsal and tags are not finished. One Local Dataset 1 photo lacks count labels.

First: fix remaining errors using training/validation photos and freeze the detector, weights and settings. Record what each member actually changes.

Next: capture and label new group-separated test images including hard conditions; run the frozen pipeline once for final scoring, with reproducible code and hashes.

Then: update report/slides/appendix and truthful contribution statements, record/rehearse on the demo laptop, and create actual checkpoint/release tags when the corresponding package is ready.

Reused ten-photo development partition: count MAE 3.00 grains; broken-percentage MAE 2.92 points. These are development values. They are not an untouched final evaluation or proof that every rubric gate is passed.
