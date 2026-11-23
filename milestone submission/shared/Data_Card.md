Dataset data card

Cristhian Sempertegui, Dataset de arroz peruano (Kaggle). Captured at a Lambayeque rice mill, August-September 2023, according to the archive README. Kaggle lists MIT and links to the supplied Mark Otto / Andrew Fong notice. Retain that notice and dataset credit.

Folder entero = whole; quebrado = broken. Mancha/stained and tiza/chalky are outside this classifier. Source integrity classes contain 4,219 images; 3,879 unique nonconflicting candidates remained, with 3,877 accepted. No independent per-image label review or capture-session IDs.

EXIF orientation, RGB conversion, foreground thresholding, morphology, grain-region filtering and geometric features. No augmentation. Approximate source resolution: 399-400 pixels per side. Baseline uses aspect ratio; tree adds solidity and ellipse fill.

Seed 42; approximately 70/15/15 by image after exact duplicate/conflict removal. The exposed development-test gallery is not an untouched final evaluation. Reencoded duplicates and shared capture sessions may remain. Fresh local photos with manual counts are still needed.

Split | Whole | Broken | Total

Train | 2,161 | 552 | 2,713

Validation | 463 | 119 | 582

Development test | 463 | 119 | 582

Accepted total | 3,087 | 790 | 3,877
