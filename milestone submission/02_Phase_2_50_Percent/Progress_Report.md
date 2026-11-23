Phase 2 | progress report

19 November 2026. This package describes the implementation available now. It is not evidence of what existed at the original 22 October deadline. Team: Zyril Dela Paz, Axcel Andrei Delos Reyes, Jhed Aeron Lachano.

An evidence-based planning estimate, not a teacher-certified mark. Ten equal implementation work packages were used: eight implemented (80%) and two pending (20%). Implementation completion does not imply that every submission gate is met.

1. Dataset audit/import. 2. Image split/sample catalog. 3. Preprocessing and grain features. 4. Aspect-ratio baseline. 5. Decision Tree. 6. Single-image/folder CLI and exports. 7. Upload/replace/sample web interface. 8. Metric and test-case tooling.

9. Independent real-photo ground truth and target verification. 10. Robust pale/crowded-scene behavior supported by evidence. Final media, fresh installation and contribution statements are additional submission gates.

582 validation grains: baseline accuracy 0.9725; Decision Tree accuracy 0.9588, macro-F1 0.9389. This is isolated-grain classification from saved features, not multi-grain counting accuracy.

---

Phase 2 | blockers and revised plan

Data acquisition/preparation, preprocessing, baseline, primary model, CLI and interface are implemented. Independent local evaluation and final hand-in preparation remain. No missing historical timeline or member ownership has been invented.

Original capture groups are absent; labels have not been independently reviewed. Development-test images have been exposed. Pale-background/composite tests retain false detections and classification errors. A fresh-clone dependency installation has not been verified; network package access was unavailable in this preparation session.

First, inspect the six bundled outputs and rehearse the CLI. Next, obtain 30 labeled local development/validation photographs and ideally 10 untouched photographs from new physical samples or capture sessions. Have two reviewers resolve label/count disagreements. Assign actual owners before work.

Improve low-contrast segmentation and look-alike classification on development data. Freeze settings, evaluate the untouched local set once, export count MAE and percentage-point MAE, and update the report. Then verify a clean clone and rehearse with the exact demo laptop.

Requirements and setup commands are in the shared source snapshot; Data_Card.pdf records preparation; six sample inputs and annotated outputs are included. The requested cp2-50 tag is still pending. Do not backdate it or describe this reconstruction as an October submission.
