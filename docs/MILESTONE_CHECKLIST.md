> Historical checkpoint assessment. Later reports, rendered slides and evidence are now published; see [current publication status](PUBLICATION_STATUS.md). Older statements about absent local files are preserved as history.

# BigasCheck milestone checkpoint review

Reviewed 12 November 2026 against the supplied Milestone 2, 3, 4, 5 and 6 guides. The two Milestone 3 PDFs contain the same requirements. Status describes available evidence, not an instructor's verdict or a completion grade.

## Milestone 2 — 50% progress

| Requirement | Status | Evidence / remaining action |
|---|---|---|
| Rebuildable CPU environment and README | Partial | Direct dependencies pinned in `requirements.txt`; `setup.ps1`, `start.ps1`, `src/predict.py` available. Fresh-machine/fresh-clone installation still needs a real run. |
| Clean, organized dataset | Implemented with limitations | Exact duplicates/conflicts excluded; physical train/validation/test folders and manifests exported by `prepare-samples`. |
| Split by source; lock untouched test set | Not satisfied | Original capture groups are unknown. Current image-level test set has already been evaluated and exposed in the gallery. Collect a fresh group-labeled local evaluation set; do not relabel the current set as unseen. |
| One-page data card, license and label checks | Partial | `docs/DATA_CARD.md` records counts, provenance and gaps. Kaggle's MIT license field and linked notice were verified on 2026-11-19; independent per-image label review remains incomplete. |
| Shared preprocessing and before/after evidence | Implemented | `bigascheck/vision.py`, `model.py`; `outputs/checkpoints/validation/preprocessing_strip.png`. |
| Reproducible validation baseline number | Implemented | `python src/evaluate.py --split validation --output outputs/checkpoints/validation`. |
| End-to-end prototype | Implemented | Flask interface, `src/predict.py`, `src/run.py`; masks, annotated output, counts and exports. |
| Progress report, real owners, tag `cp2-50` | Partial / pending | `docs/PROGRESS_REPORT.md` exists. Team ownership/history are not supplied; project is not currently a Git repository. |

## Milestone 3 — core implementation and testing

| Requirement | Status | Evidence / remaining action |
|---|---|---|
| One command from raw image/directory to output | Implemented for images | `src/run.py --input IMAGE_OR_DIRECTORY --output OUTPUT`; no video/webcam requirement in this rice-photo scope. |
| Main method vs baseline on held-out data | Development evidence only | Shape Decision Tree and aspect-ratio baseline compared on saved splits. These are image-level development results, not fresh final evaluation. |
| Accuracy, per-class P/R/F1, macro-F1, confusion matrix | Implemented | Evaluation writes `metrics.json`, `predictions.csv`, confusion-matrix PNGs and `results.md`. |
| Warmed-up CPU speed and hardware | Implemented | 3 warm-up runs; image-load + segmentation + feature + classification speed, hardware/dependencies and model hash recorded. |
| Representative case log and 10+ failures | Partial | 12 recorded demo cases, including hard cases; 23 development-test errors exported. Real-use local labels remain missing. |
| Failure causes and improvement plan | Partial | Observed error directions plus hypothesized causes recorded; independent cause/label review still required. `docs/remaining.md` ties work to these gaps. |
| Commit tag `cp3-core` and explainable contribution history | Pending | No verified Git history or per-member records. Do not create retrospective claims of authorship or earlier checkpoint completion. |

## Milestone 4 — 80% progress

| Requirement | Status | Evidence / remaining action |
|---|---|---|
| Integrated application for non-team users | Implemented | Upload/replace preview, held-out gallery, overlays, mask, counts, JSON/CSV/image downloads. |
| Confidence and processing time | Implemented with qualification | Per-grain model score and pipeline milliseconds shown. Decision-tree leaf votes are explicitly not calibrated certainty; baseline has no probability score. |
| 10+ cases with 3+ hard/edge cases and recorded results | Implemented as a software demo log | `src/test_cases.py`; 12 cases and saved expectations/results. Failing cases remain FAIL. This is not a claim of independent real-world accuracy. |
| Repeatable results from the exact weights | Implemented locally | `src/evaluate.py` records model/table SHA-256, versions and matrices. Speed varies with machine/load. |
| Per-condition analysis and independent counting/segmentation metrics | Not satisfied | Need local condition-labeled captures, manual grain counts, boxes or masks. Classifier F1 cannot stand in for detector precision, mask IoU/Dice or count MAE. |
| Draft report/slides and example-backed limitations | Partial | Report draft and slide outline prepared; rendered slides/PDF, complete related work and local experiments are outstanding. |
| Backup recording, remaining owners/dates, tag `cp4-80` | Pending | `docs/remaining.md` identifies work; team assignments and real recording/tag not available. |

## Milestone 5 — final presentation/package

**Not ready for final submission.** The guide states Thursday 19 November 2026, 11:30 PM for the hand-in, with presentations from Friday 20 November. Confirm the course announcement if the instructor changes this.

Still needed: Git repository/release tagged `v1.0`; fresh-clone rehearsal; final 150–200-word abstract and complete report PDF; 3–5 referenced related approaches; final verified dataset/license/label statement; independent local evaluation; final sample outputs/screenshots; 10–12 slides exported to PDF; backup demo video no longer than 5 minutes; true team/contribution table; submission and rehearsal.

Available now: working application, model files, source/development data, reproducible evaluation command, 12-case log, classification failure gallery, and draft documentation.

## Milestone 6 — individual technical defense

Each member must supply their own 1–2 page `Surname - Contribution.pdf`, matching actual modules and 3–5 real commits, and explain a decision, a solved problem, and learned concepts. `docs/CONTRIBUTION_TEMPLATE.md` and `docs/DEFENSE_GUIDE.md` support preparation. They are not completed or submitted individual statements. No authorship, contribution or commit links have been invented.

## Important boundaries

- Software unit/integration checks are not the same as the checkpoint's empirical evaluation.
- The application sample picker is useful for demonstration, but its exposed source test images are unsuitable as a new untouched final test set.
- No certified rice grade, mass-based broken percentage, independent local-photo accuracy, detection mAP, mask IoU/Dice, or human-reviewed label accuracy has been established.
- The report and slides must disclose failures, including false broken predictions on short whole grains and errors on crowded pale-background photos.

## Source guides

- Milestone 2 (course-provided guide; not redistributed)
- Milestone 3 (course-provided guide; not redistributed)
- Milestone 4 (course-provided guide; not redistributed)
- Milestone 5 (course-provided guide; not redistributed)
- Milestone 6 (course-provided guide; not redistributed)
