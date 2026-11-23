BigasCheck

Experimental rice grain integrity and broken proportion by count.

Zyril Dela Paz, Axcel Andrei Delos Reyes, Jhed Aeron Lachano

---

Problem and objectives

Interpretable image-to-output inspection. Proposal targets: broken F1 >= 0.80; count MAE <= 5; percentage-point MAE <= 5.

Only isolated source-grain classification has measured development evidence. Independent local counting is pending.

---

Dataset and license

Cristhian Sempertegui, Peruvian rice dataset. Kaggle lists MIT; notice preserved.

3,877 accepted: 2,713 train, 582 validation, 582 development test. Two integrity classes; exact duplicate/conflict exclusion.

Unknown capture groups, source labels not independently reviewed, development-test gallery exposed.

---

Integrated pipeline

RGB input -> thresholding -> morphology -> optional watershed -> shape features -> tree -> output.

Aspect ratio, solidity and ellipse fill. Shared vision/model code supports CLI and Flask.

---

Preprocessing evidence

Incorrect segmentation changes the shape features and grain count. Pale and touching scenes remain experimental.

---

Baseline versus Decision Tree

Baseline is stronger on validation. The development-test tree advantage is small; no general superiority claim.

Split / method | Accuracy | Macro-F1 | Broken F1

Validation / Baseline | 0.9725 | 0.9580 | 0.9333

Validation / Decision Tree | 0.9588 | 0.9389 | 0.9040

Development test / Baseline | 0.9588 | 0.9362 | 0.8983

Development test / Decision Tree | 0.9605 | 0.9409 | 0.9069

---

Errors and CPU speed

23 development-test errors: 16 whole -> broken; 7 broken -> whole. Mean CPU pipeline 46.05 ms/image, 20 images after 3 warm-ups; excludes rendering/output/web.

---

Actual sample output

Six test-source grains assembled into one image. A successful example is not an independent camera photograph.

---

Testing includes failures

9 PASS / 3 FAIL. Hard cases: scale, dim lighting, pale background, border, invalid upload and touching synthetic shapes.

All-whole and all-broken composites each misclassify one grain. Pale composite detects 37 regions for 6 reference grains.

---

Live demonstration

start.ps1 for the web interface; src/run.py for one image or a folder.

Upload and replace preview; select a sample; inspect overlay/mask; export CSV/JSON; accept an unseen image.

64-second captioned actual-output AVI. Record the real screen if the teacher requires a screen capture.

---

Limitations and next work

Independent local count/percentage MAE, segmentation IoU, capture isolation and source-label review.

Review look-alikes; improve pale contrast; refine touching-grain markers using development data. Freeze before a fresh final evaluation.

Current-format documents do not certify past milestone completion. Fresh installation, tags and real contributions remain pending.

---

References and team defense

Otsu (1979), DOI 10.1109/TSMC.1979.4310076; Vincent & Soille (1991), watershed; Pedregosa et al. (2011), JMLR 12:2825-2830; Perez Vera et al. (2026), DOI 10.3390/agriengineering8060252.

Each member must explain actual work and link 3-5 genuine commits. Contributions are deferred; account ownership is not authorship evidence.
