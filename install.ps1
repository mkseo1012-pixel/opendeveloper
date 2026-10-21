$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw 'Install Python 3.11+ from https://www.python.org/downloads/' }
& py -3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ is required' }
& py -3 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed' }
& .\.venv\Scripts\python.exe -m pip install .
if ($LASTEXITCODE -ne 0) { throw 'Package installation failed' }
Write-Host 'Installed. Run: .\.venv\Scripts\opendeveloper.exe serve'
