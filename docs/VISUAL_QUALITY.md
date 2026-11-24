# Rice visual quality — implementation status

The application now records three distinct aspects: whole/broken composition, discoloration of rice grains, and visible impurities/foreign objects. This is an image-based review, not a certified grade, mass percentage, moisture measurement or food-safety determination.

## Automatic result

The installed baseline model predicts whole/broken only. Its JSON quality section explicitly returns `not_assessed` with null counts for discoloration and impurities. A grain not flagged by this model is not evidence that it is clean. Whole/broken counts remain experimental automatic estimates. No trained discoloration/impurity classifier or measured quality accuracy is claimed.

## Manual review

After analyzing a photograph, open **Review and correct grains** under the results. Trace or correct individual objects. Mark foreign material with the **Impurity / foreign object** label. For each rice grain, choose **No visible discoloration**, **Discolored** or leave **Not assessed** when uncertain. Use **Set selected discoloration status** to review several selected objects at once. Do not infer discoloration from shadows, glare or a warm camera cast.

The reviewed summary counts impurities separately; broken percentage uses rice candidates as its denominator, not foreign objects. Unclassified rice candidates withhold that percentage. Review completion requires explicit confirmation, reviewed outlines/classes and assessed discoloration for every rice grain. The confirmation is the reviewer's assertion, not an independent label audit.

The visual-quality classification is descriptive:

- **Review incomplete**: missing outlines/classes/discoloration or no final confirmation.
- **Visible defects reported**: completed review includes discoloration or impurities.
- **Broken grains present**: completed review includes broken rice but no reported discoloration/impurities.
- **No reviewed visible defects**: completed review has whole rice and no reported discoloration/impurities.

These are not premium/Grade 1/good/fair/poor standards or safety judgements. No arbitrary commercial-grade thresholds are assigned. The automatic result stays unchanged above the manual quality result. Corrected reports identify their source as `manual_review` and retain the original automatic output and edit history. Downloaded review data stays on the user's device unless the user shares it.

## Training path

Export reviewed polygon annotations for five classes: `whole`, `broken`, `discolored_whole`, `discolored_broken`, `impurity`. This keeps discoloration separate from physical breakage: a discolored grain can be whole or broken. The prepared-dataset converter rejects unsupported classes, unreviewed polygons, unassessed rice discoloration, invalid geometry, duplicate decoded images and capture-group leakage. It does not verify that the reviewer identified every object correctly.

Read [INSTANCE_TRAINING.md](INSTANCE_TRAINING.md). The optional trainer is prepared, but no new instance/defect model has been trained, evaluated or integrated. Supply reviewed training/validation captures containing every configured class, then evaluate before replacing the automatic baseline. Regression/gallery photos already used during development are not untouched final evaluation.

## Background references

- FAO's hosted physical rice-characteristics material distinguishes discoloration, broken kernels and foreign material: https://www.fao.org/4/x5048e/x5048E03.htm (background terminology; no grading thresholds from it are implemented).
- Instance-mask training/data formats: https://docs.ultralytics.com/tasks/segment/ and https://docs.ultralytics.com/datasets/segment/.

Current verification: 65 Python tests and 8 JavaScript tests passed, including a lightweight DOM harness for review actions/exports/reset. Browser layout has not been visually tested in this session. Optional Ultralytics/PyTorch training has not run; the app's pinned SciPy environment is unchanged.
