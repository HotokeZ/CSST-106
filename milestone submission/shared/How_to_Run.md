# Run the included source snapshot
Extract BigasCheck_Source.zip to a new directory. Open PowerShell in that directory.
Python 3.13 is the tested version. Run .\setup.ps1, then .\start.ps1 for the web interface.
One-command image run after setup:
.\.venv\Scripts\python.exe src/predict.py --input sample_inputs/01_single_whole.png --output outputs/demo --background dark --connected-regions
Batch: .\.venv\Scripts\python.exe src/run.py --input sample_inputs --output outputs/demo --background dark --connected-regions
Outputs: annotated.png, mask.png, results.json, grains.csv and batch_results.json.
Software checks: .\.venv\Scripts\python.exe -m unittest discover -s tests -v
Evaluation: .\.venv\Scripts\python.exe src/evaluate.py --split test --output outputs/evaluation
The full original source PNGs must be obtained from Kaggle to reproduce timing and all failure images. Save ZIP as inputs/archive.zip, then run:
.\.venv\Scripts\python.exe -m bigascheck extract inputs/archive.zip data/raw
.\.venv\Scripts\python.exe -m bigascheck prepare-samples
The model and portable feature/split table are included; source images are excluded except for six test examples/composites.
Fresh dependency installation needs network access and remains unverified. A source-copy check using existing installed packages does not establish fresh-install success.
