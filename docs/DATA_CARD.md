# Current one-page data card

Prepared 23 November 2026. Task: detect rice and estimate whole/broken by count, not by mass or official grade.

Sources: Kaggle "dataset de arroz peruano", cristhiansempertegui, plus user-supplied Local Dataset 1 and 2. Kaggle MIT licence/linked notice verified 19 November; Mark Otto (2013) / Andrew Fong (2017) attribution preserved. User photos have separate provenance; Kaggle MIT is not applied to them.

Kaggle: train 2,713 (2,161 whole / 552 broken); validation 582 (463 / 119); reused test 582 (463 / 119). Total 3,877. Excluded stained/chalky classes, exact duplicates and contradictory duplicate labels. Folder entero=whole; quebrado=broken. Source labels are not independently audited; original capture/session groups are unknown.

Local Dataset 1: 33 photos, 32 filename-count references, 396 whole + 181 broken = 577 grains; one lacks counts. Preserved assignments: 18 train (17 labelled + 1 unlabelled), 10 development-test, 5 prior demos. Physical sample/capture groups unknown. Dataset 2: 17 training photos, 8 whole / 9 broken; user folder labels and one manually reviewed target crop each. Combined: 35 train / 10 development-test / 5 prior demos; no untouched final test set.

Tree training: 2,713 Kaggle + 17 local targets = 2,730 grains. Multi-grain count calibration uses training-photo counts. Weights/assignments unchanged here. Count labels cannot establish per-grain class accuracy. Gallery: 24 Kaggle test grains + 3 declared composites + 4 Local Dataset 2 training crops; no Local Dataset 1 entries. Gallery inputs are exposed demos, not independent evaluation.

Preprocessing: EXIF transpose, RGB, max-edge 1,600 for uploads; adaptive masks, guarded texture recovery, morphology, optional touching-region watershed; border/shape/area filters; dimensionless silhouette features. Fabric texture and small/occluded/touching grains can cause false detections, misses or splits. Full-photo and reviewed-crop performance differ.

Limits: reused test data, unknown capture groups, unadjudicated labels, no independently verified masks or final local evaluation. Raw private photos omitted from Git; intentional gallery/demo assets include provenance. Feature table, local manifests and update protocol retain memberships, counts and hashes.
