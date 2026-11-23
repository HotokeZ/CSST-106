Detector improvement | development results

The adaptive detector smooths fine cloth weave, subtracts local illumination, suppresses strongly saturated fabric colors, removes tiny/frame background regions before watershed, and rejects implausible elongated or fragmented shapes. Uniform-border scenes retain the previous foreground path.

Same 32 filename-count references, same 1600-pixel JPEG preparation, same saved whole/broken classifier and original model hash. The uncounted 33rd image is processed but unscored. These images guided detector refinement: the results are development comparisons, not an untouched test.

Tree count MAE: 477.81 -> 7.94 grains, a 98.3% reduction. Tree broken-percentage MAE: 49.96 -> 34.57 percentage points. Remaining failures and the stronger percentage baseline are retained.

Version / classifier | Count MAE | Pct-point MAE | Within 5 grains

Original / Baseline | 477.81 | 39.44 | 2/32

Original / Tree | 477.81 | 49.96 | 2/32

Improved / Baseline | 7.94 | 20.83 | 22/32

Improved / Tree | 7.94 | 34.57 | 22/32

---

Limits, checks and reproduction

34 software tests pass, including synthetic woven surfaces, saturated fabric rejection, uniform-background preservation and the existing archive/split/API/model tests. The original model is unchanged. Per-photo results are checked against the original reference rows before comparison.

Mean image decode + tree pipeline after the first image: 7550.56 -> 1044.92 ms/image. Different system load can affect this comparison; original resizing, rendering and output writes are excluded.

Silhouette errors and naturally short whole grains still affect integrity predictions. This change does not establish per-grain F1 or mask IoU. Do not claim final target compliance from development data, even if a numeric target is met here. Strong color casts, pale surfaces and heavy overlap remain challenging.

python src/evaluate_local.py --detector adaptive --output outputs/local_reproduction_v2
Use --detector legacy with a new output folder for the old path. App and CLI now default to adaptive detection; legacy remains selectable. API/CLI inputs are proportionally limited to 1600 pixels for consistent adaptive processing.

Condition | N | Old count MAE | New count MAE

Separated | 12 | 545.50 | 0.92

Overlap | 10 | 388.80 | 5.20

Lighting/BG | 10 | 485.60 | 19.10

---

Actual before/after outputs

Lighting/background, overlap and separated examples are shown in rows. Compare masks and per-photo errors rather than treating a larger region count as success. All 32 scored cases remain in comparison.csv.
