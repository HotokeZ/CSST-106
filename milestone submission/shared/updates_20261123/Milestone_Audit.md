# Milestone audit - 23 November 2026

**The milestones are not all complete.** The application, current weights, gallery and image pipeline run, but a file's presence does not establish that its claims match the current code or that a required untouched evaluation has occurred. This review uses the requirements supplied in the conversation; no instructor sign-off is inferred.

## Phase 2 - 50% progress

| Required hand-in | Current evidence | Status / remaining action |
|---|---|---|
| Pinned environment; README fresh setup | requirements.txt; setup/start scripts; isolated install with user site disabled; exported app/model/gallery ran without raw data | Verified on this Windows laptop; exact tagged fresh-clone rehearsal still needed after tagging |
| Dataset acquired; train/validation/test; one-page data card | Kaggle split 2,713/582/582; local manifests; latest one-page data card in shared/updates_20261123 | Available with unknown capture groups and previously exposed test split disclosed |
| Preprocessing/feature extraction in source | src/preprocess.py; bigascheck/vision.py and foreground.py | Implemented |
| Baseline or model; measured validation result | src/evaluate.py, 582 validation grains, current validation metrics and matrices | Measured; tree accuracy 95.70%, macro-F1 0.9369 |
| One-command prototype | python src/predict.py --input IMAGE --output DIRECTORY | Implemented; working image pipeline |
| Six screenshots/sample outputs | Existing shared/sample_inputs and sample_outputs; newest patterned example and masks | Present; older images retain their original provenance |
| One-to-two-page progress report | Latest two-page Progress_Report.pdf in shared/updates_20261123 | Available; earlier proposal dates are not backdated |
| cp2-50 tag; repository link | Repository exists and current work is published | Tag pending; no earlier checkpoint date is claimed |

## Phase 3 - core implementation and testing

| Required hand-in | Current evidence | Status / remaining action |
|---|---|---|
| Primary method integrated; one command input to annotated output/counts | Adaptive segmentation, touching-grain split, features, pooled tree/count calibration, crop editor, CLI/Flask | Implemented for image scope |
| Fixed representative set never trained or tuned on; hard cases; test log | Current local before/after CSV; twelve-case demo; all previously used development/training images | Not satisfied: collect a new independently held-out capture set and freeze it before final testing |
| Baseline/main table and speed on that set | Current source and local development tables, hardware/protocol and timings | Development evidence available; required untouched-set comparison remains pending |
| Ten failures by cause; confusion matrix if classifying | Current test tree has 22 logged failures, contact sheet, hypothesised cause groups and matrices | Present for source classification; physical cause/label review remains limited |
| Three improvements tied to causes | Latest four-page Results_Addendum.pdf | Present; classification and false background regions remain issues |
| Two-to-four-page results PDF; cp3-core tag | Latest four-page addendum plus historical Core_Results.pdf | Current addendum exists; independent results and actual tag pending |

## Phase 4 - 80% progress

| Required hand-in | Current evidence | Status / remaining action |
|---|---|---|
| Nearly complete app and results interface | Upload/replace preview, crop editor, Kaggle-first sample gallery, boxes/labels/counts/mask/exports/time | Implemented; classification and uncropped Local Dataset 2 false detections remain |
| Held-out evaluation via src/evaluate.py; speed; change since checkpoint 3 | Current reproducible source tree metrics; local development before/after evidence | Independent final set still missing; do not call reused source test data untouched or fabricate historical checkpoint numbers |
| Performance and limitations | Current addendum discloses pattern 9/3 vs 8/4 and uncropped Local Dataset 2 error | Available; incorporate in revised technical report |
| Ten test cases including three hard/edge cases | Current twelve-case log: 9 pass / 3 fail, including lighting, scale, crop/border, pale background, invalid upload and synthetic touching cases | Current log available; failures remain FAIL |
| Draft technical report and eight-plus draft slides | Existing 12-page report and 12-slide PDF | Files exist; method/data/results text must be revised to current code and evidence |
| Backup demo up to five minutes | Existing 64-second generated actual-output AVI | Historical output walkthrough; record the updated app/gallery/crop flow and rehearse |
| cp4-80 tag and agreed remaining-task list | This audit lists remaining work | Tag and teacher/team agreement pending |

## Final team submission

| Required hand-in | Current evidence | Status / remaining action |
|---|---|---|
| Final app, complete source, README, weights and sample inputs; v1.0 | Working project, current model, portable gallery, scripts and repository | Source ready to review; final acceptance, exact tagged rehearsal and v1.0 pending |
| Complete final report PDF | Existing Final_Technical_Report.pdf is a final-format draft and repeats older method/results | Revise data/method/experiments/results/limitations, append current evidence and real contribution table; final checks pending |
| Screenshots/output folder and report appendix | Existing six-output appendix; newest pattern evidence | Present; update appendix/captions for the current app |
| Final slides PDF and backup demo up to five minutes | Existing 12-slide PDF and historical AVI | Update and rehearse with the actual demo laptop; every member must explain their part |
| Representative teacher-supplied inputs and Q&A | Software supports file input | Live defence/rehearsal cannot be certified from files |

## Individual defence

Three contribution forms are drafts. Each member still needs a truthful one-to-two-page `Surname - Contribution.pdf` with their modules/functions and 3-5 real key commits, one decision and rejected alternative, one solved problem, and two learned concepts. Contribution work remains deferred as requested; no authorship or evidence is invented. A publication commit is not proof that each member wrote every file.

## Remaining actions

1. Collect new capture-grouped evaluation photos, including dim/patterned, textured single-grain, pale/crowded and touching cases. Record whole/broken counts; add per-grain labels/boxes if reporting classification/detection precision. Keep these images out of training/tuning and the demonstration gallery until final scoring.
2. Address remaining classification mistakes and full-frame background false detections using training/validation material; freeze code, weights and settings before final evaluation. Count targets do not identify each grain's class.
3. Revise the main report and slides around current evidence and remaining limitations. Use the latest one-page card, two-page progress report and four-page results addendum now available; historical PDFs/ZIPs are not current submissions by themselves.
4. Complete real contributions when the team is ready; record/rehearse the updated application on the demo laptop.
5. Create the actual checkpoint/release tags when their hand-ins are ready and rehearse from each exact tag. Tags are not created automatically by this audit and must not imply retroactive completion.

Current evidence: shared/updates_20261123 under milestone submission. Known development results and software checks do not replace independent evaluation, a teacher mark or member understanding. The earlier raw-data split memberships are preserved; changing the demonstration gallery does not create new held-out data.
