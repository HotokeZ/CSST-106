param(
    [string]$Archive = (Join-Path $env:USERPROFILE 'Downloads\archive.zip')
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = if (Test-Path -LiteralPath '.venv\Scripts\python.exe') { '.venv\Scripts\python.exe' } else { 'python' }
if (-not (Test-Path -LiteralPath 'data\raw\Readme.md')) {
    if (-not (Test-Path -LiteralPath $Archive)) { throw "Dataset ZIP not found: $Archive. Supply -Archive with its full path." }
    & $projectPython -m bigascheck extract $Archive data/raw
    if ($LASTEXITCODE -ne 0) { throw 'Dataset extraction failed.' }
}
if (-not (Test-Path -LiteralPath 'data\peruvian_source.csv')) {
    & $projectPython -m bigascheck prepare-peruvian data/raw data/peruvian_source.csv
    if ($LASTEXITCODE -ne 0) { throw 'Dataset preparation failed.' }
}
& $projectPython -m bigascheck train data/peruvian_source.csv --source-labels --max-area-fraction 0.6 --output artifacts
if ($LASTEXITCODE -ne 0) { throw 'Training failed. Read the error above.' }
& $projectPython -m bigascheck train-shape --features artifacts/features_and_splits.csv --output artifacts
if ($LASTEXITCODE -ne 0) { throw 'Shape classifier training failed.' }
& $projectPython -m bigascheck prepare-samples --features artifacts/features_and_splits.csv --output data/splits
if ($LASTEXITCODE -ne 0) { throw 'Preparing test samples failed.' }
Write-Host 'Model saved to artifacts/model.joblib. Restart the app with python app.py.'
Write-Host 'This initial model uses source labels and an image-level split. Validate on independent local samples.'
