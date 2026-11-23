# Crop-context regression — 24 November 2026

The two user reports refer to the same IMG_20261121_005008.jpg (1815 × 1362), reference 18 whole / 3 broken. Before this change, the exact tight crop returned 18 candidates and the wide crop returned 22. Both now return 21 candidates and 19 whole / 2 broken through the upload API. Classification still has one error; these development regressions are not independent final accuracy evidence.

Cropped adaptive analysis now computes the foreground on the original image, then selects the crop mask. Crop coordinates and foreground_context=original_image are included in the result. No expected count or filename controls detection. Smooth-boundary merging rechecks merged silhouettes until no further merges occur, and uses a grain-like elongation check. The exact API crops and three reviewed middle-grain positions are tested in tests/test_intensity_separation.py. Private photos are omitted from Git, so those photo-dependent tests skip without the local image.

Validation: existing 58 tests passed; after adding the two-crop API regression, all five intensity-separation tests passed. The observed 21 candidates do not establish correct masks or classification on other crops/photos.
