# BigasCheck progress evidence

Status date: 12 November 2026. The current folder is not a Git repository. Team owners and per-member history have not been supplied; they must be filled from actual work rather than inferred from this document.

| Task | Owner | Status | Evidence |
|---|---|---|---|
| Source inventory, cleaning and image split | Unassigned | Implemented; session isolation unresolved | `dataset.py`, `samples.py`, data card |
| Shared preprocessing and shape extraction | Unassigned | Implemented | `vision.py`, preprocessing strip |
| Baseline and Decision Tree | Unassigned | Implemented, development results only | `model.py`, exact saved weights |
| Upload/replace and test gallery | Unassigned | Implemented | `app.py`, `templates/`, `static/` |
| One-command image/directory run | Unassigned | Implemented for photographs | `src/run.py`, `src/predict.py` |
| Reproducible classification evaluation | Unassigned | Implemented | `src/evaluate.py`; metrics and matrices |
| Speed and failure evidence | Unassigned | Measured/exported; cause review pending | `outputs/checkpoints/` |
| 12 demo cases, including hard cases | Unassigned | Recorded, with failures retained | `src/test_cases.py`, case results |
| Manual local dataset and final evaluation | Unassigned | Not done | Required to establish real-use performance |
| Git history, milestone tags, team statements | Each member | Not verified | Must match actual history |
| Final report, slides, backup video | Unassigned | Draft report/outline only | Final PDFs/video outstanding |

No overall percentage is certified: the team has not assigned effort weights/owners and several checkpoint gates remain unsatisfied. For the submitted progress report, agree on task weights, calculate completed weight / total weight, and attach the evidence above. Do not infer completion from the number of software tests.

Blockers: unknown original capture groups/license verification; absent local annotations; no verified Git/contribution history; clean-environment install not yet tested; final artifacts and rehearsal outstanding. Planned hand-in from the supplied guide: 19 November 2026, 11:30 PM. Assign internal dates and owners in `remaining.md`.
