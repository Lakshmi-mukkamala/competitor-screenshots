$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
if (-not $env:CONDA_PREFIX -or $env:COMPETITOR_SCREENSHOTS_ENV -ne '1' -or $env:CONDA_DEFAULT_ENV -eq 'base') {
  throw 'First create the environment from environment.yml and run: conda activate ./.conda-env'
}
# The runner verifies Python and its packages belong to the active environment.
python capture.py --install-browser
if ($LASTEXITCODE -ne 0) { throw 'Environment setup failed. See the error above.' }
Write-Host 'Ready. Run: python capture.py --list'
Write-Host 'Run tests: python -m unittest discover -s tests -v'
Write-Host 'Capture all pages: python capture.py'
