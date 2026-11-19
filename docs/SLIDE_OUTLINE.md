# Presentation source outline — 10 slides

This is a draft content outline, not a rendered deck or submitted PDF. Use real charts/images from the referenced outputs and complete the remaining evidence before final export. The guides request an 8+ slide draft and 10–12 final slides.

1. **Problem and scope.** Experimental rice grain integrity and broken proportion by count. State controlled-image conditions and who the prototype helps.
2. **Objectives.** Show the proposal targets and mark which have only development evidence versus no independent measurement yet.
3. **Dataset.** Show source/license status, one whole and broken example, 2,713/582/582 split, cleaning and unknown capture groups. Disclose that the test gallery is exposed.
4. **Pipeline.** Use the workflow in `REPORT_DRAFT.md`; point to the actual shared functions used by CLI and app.
5. **Segmentation and features.** Place `outputs/checkpoints/validation/preprocessing_strip.png`; explain Otsu, morphology, watershed and the three shape features.
6. **Baseline vs current.** Use the report's validation and development-test table. The baseline wins on validation; do not claim the tree is universally better.
7. **Per-class errors and speed.** Use the development-test confusion-matrix PNG, 23 errors, exact weight hash and the warmed-up CPU scope. Explain macro-F1 and the uncalibrated model score.
8. **Sample outputs and a failure.** Show a correctly analyzed six-grain composite plus a whole→broken failure and the crowded pale-background photo. The composite is synthetic assembly, not an independent capture.
9. **Live demo plan.** Upload/replace image, choose a held-out sample, show mask/score/time/download, then run a teacher-supplied image with `src/run.py`. Keep the 12-case log and a ≤5-minute backup recording ready.
10. **Limitations, next work and contributions.** Fresh local group-labeled evaluation, reviewed masks/counts/license, real ownership and commit links. Leave time for individual defense.

Final exports still needed: slides PDF, final report PDF, screenshots/sample-output appendix, backup video and actual contribution statements. Do not describe this outline as the completed presentation deliverable.
