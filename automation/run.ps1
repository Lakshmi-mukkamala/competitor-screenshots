# Run from Task Scheduler or a terminal; all arguments are passed to capture.py.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.conda-env/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create the project Conda environment first. See README.md.'
}
$env:CONDA_PREFIX = Join-Path $projectRoot '.conda-env'
$env:CONDA_DEFAULT_ENV = $env:CONDA_PREFIX
$env:COMPETITOR_SCREENSHOTS_ENV = '1'
$env:PYTHONNOUSERSITE = '1'
& $pythonPath (Join-Path $projectRoot 'capture.py') @args
exit $LASTEXITCODE
