Local photographs | evaluation addendum

33 local camera photographs: 12 separated, 10 lighting/background cases, and 11 overlap cases. Counts were read from filenames. 32 photos have counts; IMG_20261120_195353.jpg has none and is excluded from scored summaries. Whole-only filenames imply zero broken, pending user confirmation.

Originals preserved. EXIF-transposed RGB working copies were resized proportionally to a maximum 1600-pixel edge using LANCZOS and saved as JPEG quality 95. Automatic background and watershed enabled; all other settings came from the saved model. This evaluates the standardized copies, not native-resolution web uploads.

The saved model was frozen and its hash checked after execution. All supplied photos were processed without selecting favorable predictions. The same detected regions support an aspect-ratio baseline and the Decision Tree. Exact settings, hashes and first-run outputs are retained.

Photo IDs identify files. A sample would identify the same physical rice pile/batch; a capture group would identify related shots that must stay together across training and final test. Both are unknown here. All photos remain evaluation-only; no independent group count or capture-level confidence interval is claimed.

Counts are supplied by the user through filenames, not independently reviewed per-grain labels or masks. Local photos do not inherit the Kaggle dataset license. Raw photos are kept local; working evidence has no copied EXIF metadata.

---

Measured local results

Count MAE is the mean absolute difference between detected and actual total grains. Percentage MAE is the mean absolute broken-proportion error in percentage points. Both methods use the same segmentation, so their total count errors are identical.

Count MAE <= 5 grains: NOT MET. Broken-percentage MAE <= 5 points: NOT MET. Per-grain F1 is not identifiable from aggregate counts. No detection precision, mAP, IoU or classification confusion matrix is invented.

Mean working-image decode + tree pipeline after excluding the first recorded warm-up: 7550.56 ms/image. Excludes original resizing, annotation and file output. 0 labeled photos have zero detections. Percentage MAE is withheld if any are unscorable; conditional MAE is stored separately with its denominator.

Condition / method | Count MAE | Pct-point MAE | N

All labeled / Base | 477.81 | 39.44 | 32

All labeled / Tree | 477.81 | 49.96 | 32

Separated / Base | 545.50 | 52.96 | 12

Separated / Tree | 545.50 | 64.87 | 12

Overlap / Base | 388.80 | 23.36 | 10

Overlap / Tree | 388.80 | 34.92 | 10

Lighting/BG / Base | 485.60 | 39.31 | 10

Lighting/BG / Tree | 485.60 | 47.10 | 10

---

Actual outputs | largest count errors

Examples are selected by largest absolute count error, not presented as successes. See per_photo_results.csv for all cases, including failures. Count-level references cannot identify which individual boxes are false positives or missed grains.

---

Interpretation and remaining work

Real local photographs now supply an initial count/percentage evaluation across controlled, lighting/background and overlap conditions. These results supplement the earlier isolated-source-grain results; they do not replace them or establish capture-level independence.

One photo has no counts. Confirm the whole-only means zero-broken convention. Review counts independently and identify reused physical grains/capture sessions if possible. Per-grain integrity labels and masks are still unavailable.

Keep this first frozen evaluation intact. If these photos guide fixes, call them development data and obtain new physical samples/sessions for an untouched final test. Prioritize foreground/texture and overlap errors based on reviewed masks, then ambiguous whole/broken shapes. Do not tune repeatedly against these results while continuing to call the set untouched.

python src/import_local_photos.py --archive "path/to/Bigas Check Local Photos.zip"
python src/evaluate_local.py --output outputs/local_reproduction
Original archive must be available; the default first-run output refuses overwriting. The manifest, protocol, working inputs, masks, annotations, per-photo CSV and metrics are retained.

Please supply whole and broken counts for IMG_20261120_195353.jpg. This observation is unscored; no counts have been guessed.
