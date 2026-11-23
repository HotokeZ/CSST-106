# Installed detector recovery - 20 November 2026

The pale/shadow recovery is now installed directly in the Windows project and the actual localhost:5000 app has been restarted and verified over HTTP. No manual patch download/install is needed.

Changes: neutral pale-background recovery when the adaptive path finds no accepted grains; blue-cloth bright-island filtering to suppress shadow transitions; conservative size-relative noise filtering; preservation of small, bent components instead of splitting every distance maximum. The saved classifier and reference counts are unchanged. Original files were backed up under `outputs/patch_backups/20261120T135606Z`.

## Verified native uploads through the running app

| Photo / setting | Reference total | Detected | Whole / broken prediction |
|---|---:|---:|---|
| Blue cloth, minimum area 30 | 10 | 10 | 3 / 7 (incorrect integrity labels) |
| Blue cloth, minimum area 500 | 10 | 9 | 3 / 6 (small grain excluded) |
| Green cloth, minimum area 30 | 18 | 18 | 16 / 2 (incorrect integrity labels) |
| Original pale rice photo | Unannotated | 130 | Experimental; not ground truth |
| Second original pale rice photo | Unannotated | 186 | Experimental; not ground truth |

The minimum-area control means square pixels of a detected region, not image resolution. A real small fragment in the blue photo falls below 500 pixels squared. Use the default 30 and rely on foreground rejection; increasing this cutoff cannot distinguish grain from background on its own. The UI now states the correct units and this limitation.

The ten blue-photo positions were checked individually with reviewed working-image rectangles: exactly one candidate per grain and no additional candidate. Correct total alone is not proof of correct detection. Whole/broken predictions remain unreliable: correct totals have not solved integrity classification.

## Development comparison

On the same 32 filename-count reference JPEGs (longest edge 1600), Decision Tree count MAE changed from **7.9375 to 4.8125 grains** and broken-percentage MAE from **34.5733 to 29.7909 percentage points**. The numeric count target is met on this development cohort; independent final performance is not established. Shape-baseline percentage MAE is 15.2127 points, still above the 5-point target. Photos guided changes; physical sample/capture groups remain unknown. One uncounted local photo is excluded from scoring.

34 existing software checks and two additional regression checks passed. New checks cover each real blue-photo grain position and pale-mask recovery without false counts on a blank surface. Exact live responses: `outputs/patch_backups/running_app_checks.json`. First installed checks and the intermediate patch are preserved. Full current development evidence: `outputs/local_20261120_recovery_v4`, with protocol, code hashes/snapshot, per-photo JSON/masks/annotations and metrics.

Reproduce: `python src/evaluate_local.py --detector adaptive --output outputs/local_recovery_reproduction`. Never overwrite the prior evaluation. Collect fresh physical samples/sessions before final research claims, and obtain independently reviewed per-grain labels before adapting the integrity classifier.
