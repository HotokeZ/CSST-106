# Adaptive detector development comparison - 20 November 2026

The detector now suppresses textile texture and saturated fabric, normalizes local illumination, and removes invalid components before watershed. App and CLI adaptive inputs use a maximum 1600-pixel edge; explicit legacy mode is retained. The saved classifier was not retrained.

Same 32 filename-count references: count MAE **477.8125 -> 7.9375** (98.3% reduction); tree broken-percentage MAE **49.9581 -> 34.5733** percentage points. These are development results after inspecting these photos, not independent final-test accuracy. 34 software tests pass. Source capture/physical sample groups are unknown, and one local photo is still missing counts.

Evidence: outputs/local_20261120_adaptive_v2, including protocol/code hashes and a code snapshot, all 33 annotations/masks, 32 scored cases, comparison.csv and Detector_Improvement_Report.pdf. Original results remain in outputs/local_20261120_frozen; the intermediate adaptive_v1 run is retained.

Reproduce: `python src/evaluate_local.py --detector adaptive --output outputs/local_reproduction_v2`. CLI legacy comparison: `python src/run.py --input path/to/photo.jpg --output outputs/legacy --detector legacy`. Default app/CLI now use adaptive detection. Controls and data preparation are recorded in the report.

Improvement priorities remaining: review per-grain integrity labels from local crops, measure detector misses/false boxes with annotations, and obtain fresh photos from new physical samples/sessions before claiming final performance. Aggregate counts cannot produce a per-grain confusion matrix or F1.
