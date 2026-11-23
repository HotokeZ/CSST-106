# Repository publication — 23 November 2026

This snapshot publishes the current Bigas Check application, active trained model, training/import/evaluation tools, crop editor, tests, and the existing milestone documents and evidence. It does not certify that every course checkpoint is complete.

## Validation

- Current working folder: 46 automated tests passed.
- Clean export directory with raw/private datasets omitted: 46 tests discovered, 43 passed and 3 data-dependent tests skipped.
- Exported Flask app: home page returned HTTP 200; the supplied current model loaded with no model error using the SciPy backend.
- These checks used the existing installed Python environment. A fresh dependency installation has not been demonstrated here.

## Included and excluded files

The active `artifacts/model.joblib` is copied byte-for-byte from the current project. The public Kaggle feature table uses relative paths; its numeric values, labels and split membership are unchanged. The original feature-table fingerprint recorded in historical run reports can therefore differ from the published portable CSV fingerprint.

Raw datasets, incoming ZIP files, `.codex`, transfer helpers, caches, runtime outputs and virtual environments are excluded. Phase PDFs, presentation PDFs, case logs, sample outputs, failure galleries, the generated backup AVI and draft contribution forms are included under `milestone submission/`. Redundant complete-package ZIPs, the older nested source snapshot and their local archive-check manifests are omitted. The repository root is the source of truth for the current application.

## Results and milestone status

Existing reports and example outputs preserve their recorded runs. The current detector was edited after some reported local experiments, so those figures must not be represented as a fresh benchmark of this publication. `artifacts/evaluation.json` is a historical source-only training report; the later combined/single-grain reports are under `docs/evidence/`. Re-run the current evaluators with the corresponding data and record the exact weights/code before submitting new performance claims.

The milestone folders contain prepared reports, slides and a generated actual-output walkthrough, but still require review against the final runnable code, an independent final evaluation set, fresh installation/demo rehearsal, and actual member contribution evidence. Contribution forms remain drafts. No checkpoint or final-release tags are fabricated as part of this publication.

Gallery selection and the reported patterned-background failure have not been changed by this repository synchronization. This commit preserves the current detector and interface behavior.
