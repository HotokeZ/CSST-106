BigasCheck

Final-format technical report | 19 November 2026
Zyril Dela Paz, Axcel Andrei Delos Reyes, Jhed Aeron Lachano

Runnable development prototype with measured source-grain results. Independent local evaluation, actual contributions, fresh installation verification and release tags remain pending. This report documents those limitations explicitly.

BigasCheck examines photographs of rice grains to estimate visible grain integrity and broken-grain proportion by count. The prototype combines threshold-based segmentation, morphological cleanup, optional distance-transform watershed, and an interpretable Decision Tree. A public Peruvian rice dataset supplied whole and broken reference labels. After removing duplicate or conflicting files and screening unusable images, 3,877 grain images remained, divided into 2,713 training, 582 validation, and 582 development-test instances. The current classifier uses dimensionless silhouette features so that uniform image scaling and background color do not directly determine its inputs. On the reused development-test split, the classifier achieved 96.05% accuracy, macro-F1 of 0.9409, and broken-grain F1 of 0.9069. These figures describe isolated-grain classification, not independent multi-grain counting or segmentation accuracy. The application supports image upload, replacement previews, held-out sample selection, annotated results, and downloadable reports. Source capture groups and independent label checks remain unavailable, while crowded pale-background photographs produce substantial errors. Fresh local annotations and a previously unused capture-level evaluation set are therefore required before claiming reliable real-world rice-quality estimates.

---

1 | Problem and objectives

Rice photographs contain variations in grain shape, illumination and contact between grains. BigasCheck explores a transparent computer vision workflow for detecting candidate grains, classifying visible integrity and estimating broken grains by count.

Provide a repeatable image-to-output application and source-grain whole/broken classifier.

Compare a geometric baseline with a Decision Tree using separate training, validation and development-test image assignments.

Proposal targets: broken-grain F1 >= 0.80, count MAE <= 5 grains, and broken-percentage MAE <= 5 percentage points. Independent local count and percentage targets are not yet measured.

Static photographs and a local Flask demonstration. Outputs use pixel measurements. No physical calibration, official grading, mass-based broken fraction, cultivar identification or validated visible-defect grading is claimed.

---

2 | Related approaches

Otsu selects a grayscale threshold through between-class separation. It provides a simple foreground stage for rice on a contrasting background, but low contrast and uneven lighting motivate separate handling.

Vincent and Soille describe watershed segmentation in digital spaces. BigasCheck uses distance-based markers to separate touching foreground regions. The implementation is not claimed to reproduce their exact algorithm; marker quality and overlap still affect outputs.

Scikit-learn provides supervised classifiers, including Decision Trees. Shape descriptors allow compact, inspectable rules, but similar whole/broken silhouettes limit separability. Depth and leaf-size constraints restrict complexity.

Perez Vera and colleagues compare pretrained CNNs on four Peruvian rice defect classes. Their four-class task and experimental protocol differ from this two-class shape prototype, so their reported scores cannot be ranked directly against our results. Learned appearance models are a future alternative, not part of this implementation.

---

3 | Dataset and preparation

Public dataset: Cristhian Sempertegui, Dataset de arroz peruano. The archive contains 6,599 categorized PNGs plus four viewer images. Kaggle lists MIT and links to the preserved notice. The archive credits a Lambayeque rice mill and capture during August-September 2023.

Source folder labels entero and quebrado become whole and broken. Mancha and tiza are excluded. Exact duplicates and conflicting labels are removed; readability and single-region screening retain 3,877 grain images. Source labels have not received independent human review.

Seed 42; approximately 70/15/15 by image, with exact byte hashes disjoint across splits. Original capture-session IDs are unknown. Exposed development-test images cannot support an untouched final-evaluation claim. No training augmentation was used.

Split | Whole | Broken | Total

Train | 2,161 | 552 | 2,713

Validation | 463 | 119 | 582

Development test | 463 | 119 | 582

---

4 | Methodology and algorithms

Apply EXIF orientation and RGB conversion. A dark-background path uses grayscale Otsu; pale-background mode combines foreground thresholding and local contrast. Morphology removes noise and fills small holes. Region size and border checks remove incomplete or implausible regions.

Optional distance-transform watershed partitions connected foreground. The shape classifier uses major/minor-axis aspect ratio, area/convex-hull area (solidity), and area/(major-axis x minor-axis), called ellipse fill in the code. Uniform scaling approximately preserves these descriptors; segmentation errors do not disappear.

An aspect-ratio threshold forms the baseline; the current tree has maximum depth 5 and minimum leaf size 10. Predicted whole/broken regions are counted. Broken percentage = 100 x predicted broken / detected grains. Zero-region inputs do not produce a fabricated zero-percent quality result.

The interface shows a Decision Tree leaf-vote score, not calibrated certainty. Pixel measurements are not millimeters. Candidate regions should be visually checked.

---

5 | Software and reproducibility

Pinned Python package versions are in requirements.txt; the measured environment uses Python 3.13.3 on Windows, CPU/SciPy segmentation. OpenCV is optional and changes backend behavior; keep the tested default environment for these weights.

Setup: .\setup.ps1. Web demonstration: .\start.ps1.

Single image: python src/predict.py --input sample_inputs/01_single_whole.png --output outputs/demo --background dark --connected-regions.

Folder: python src/run.py --input sample_inputs --output outputs/batch --background dark --connected-regions.

Evaluation: python src/evaluate.py --split test --output outputs/evaluation. The complete source PNG dataset is required for speed/failure rendering; the included feature table supports metric reproduction.

The source snapshot includes model.joblib, the portable feature/split table and six sample inputs. Full raw data and personal photographs are excluded. The gallery is rebuilt from the Kaggle ZIP with extract and prepare-samples commands in README.md.

Current-environment software checks and pipeline runs are logged. A clean source copy is checked separately from a fresh dependency installation. Network package access was unavailable, so a new dependency installation is not certified.

---

6 | Experiments and results

Validation guides model selection. Development-test metrics are descriptive because those images have been exposed in the gallery. Feature-table classification and image pipeline timing are different measurements; neither directly measures detection precision or segmentation IoU.

The baseline wins on validation. The tree is slightly higher on development test. These results do not establish a general tree advantage. Class imbalance makes macro-F1 and broken-class F1 useful alongside accuracy.

Current CPU means: 46.03 ms/image (validation), 46.05 ms/image (development test). Twenty images after three warm-ups, model loaded once; output rendering, browser transport and file writing excluded. Logs retain hardware and exact model/data hashes.

Split / method | Accuracy | Macro-F1 | Broken F1

Validation / Baseline | 0.9725 | 0.9580 | 0.9333

Validation / Decision Tree | 0.9588 | 0.9389 | 0.9040

Development test / Baseline | 0.9588 | 0.9362 | 0.8983

Development test / Decision Tree | 0.9605 | 0.9409 | 0.9069

---

7 | Error analysis and test cases

The tree makes 23 errors among 582 development-test grains: 16 whole -> broken and 7 broken -> whole. Broken precision is 0.8750 and recall 0.9412. Gallery cause assignments are hypotheses pending label and contour review.

The recorded log contains 9 PASS and 3 FAIL. All-whole and all-broken six-grain composites each have one integrity error. A pale-background six-whole composite yields 37 candidate regions, including 6 predicted broken. These failures are retained rather than hidden.

Cases include half-resolution, dim lighting, frame-cut grain, invalid upload, blank input, pale background and touching synthetic ellipses. These are repeatable software fixtures, not independent natural-camera accuracy evidence.

---

8 | Limitations and conclusion

No independent local whole/broken annotations, manually verified multi-grain counts, detection boxes or masks are available. Count MAE, percentage-point MAE, mAP and IoU are therefore unreported. Pale/crowded scenes remain unreliable; source capture groups and manual label review are missing.

The development broken F1 exceeds the numeric proposal threshold on isolated source grains, but does not verify local-grain performance. Multi-grain count and broken-percentage objectives remain unverified. Larger detected counts do not demonstrate correctness.

The project implements an interpretable local pipeline, web interface, split-preserving sample gallery and reproducible development metrics. It is suitable for demonstrating the method and its failure modes. Reliable field or rice-quality claims require fresh capture-level evaluation and stronger segmentation evidence.

Review reference labels; collect 30 local development/validation photos plus ideally 10 untouched new sample/session photos; improve segmentation and ambiguous shapes on development data; freeze settings and evaluate once; verify a clean installation, complete individual statements and rehearse before release.

---

9 | Contributions and hand-in status

Names are supplied by the team. Contribution assignments and commit links were deliberately deferred and are not inferred from repository account ownership.

Each member must supply actual modules, 3-5 genuine commits, a technical decision, a solved problem and two learned concepts. The individual PDFs are visibly marked drafts. Do not submit them as completed personal statements.

Requested tags are cp2-50, cp3-core, cp4-80 and v1.0. No past checkpoint work or teacher assessment has been reconstructed as historical fact. Tags are not created by this package builder. Tag only reviewed real commits and describe any present-day reconstruction honestly.

Independent local evaluation; real contribution table/statements; fresh dependency installation verification; teacher acceptance of the captioned output-walkthrough backup versus a live UI screen recording; tag/repository artifact upload verification.

Member | Confirmed contribution

Zyril Dela Paz | Pending member confirmation

Axcel Andrei Delos Reyes | Pending member confirmation

Jhed Aeron Lachano | Pending member confirmation

---

10 | References

A Threshold Selection Method from Gray-Level Histograms. IEEE Transactions on Systems, Man, and Cybernetics, 9(1). DOI: 10.1109/TSMC.1979.4310076.

Watersheds in Digital Spaces: An Efficient Algorithm Based on Immersion Simulations. IEEE Transactions on Pattern Analysis and Machine Intelligence. Author-hosted paper: people.cmm.minesparis.psl.eu/users/marcoteg/cv/publi_pdf/MM_refs/vincent/1991_PAMI_VincentSoille_watershed.pdf

Scikit-learn: Machine Learning in Python. Journal of Machine Learning Research, 12, 2825-2830. https://www.jmlr.org/papers/v12/pedregosa11a.html

Decision Trees. https://scikit-learn.org/stable/modules/tree.html (accessed 19 November 2026). The experiment uses pinned version 1.7.2; current online documentation may describe a later version.

Deep Learning Models for Defect Identification in Oryza sativa Rice Grains: A Comparative Study. AgriEngineering, 8(6), 252. https://doi.org/10.3390/agriengineering8060252

Dataset de arroz peruano. https://www.kaggle.com/datasets/cristhiansempertegui/dataset-de-arroz-peruano. Publisher lists MIT; linked notice: https://www.mit.edu/~amini/LICENSE.md. Course checkpoint requirements supplied by the team are the submission specification.

---

Appendix A | six actual sample outputs

Each image below is an actual annotated output generated by the saved model. Inputs, masks, grain CSV and JSON are in shared/sample_inputs and shared/sample_outputs. Source labels/composite counts are references, not independently reviewed local ground truth.
