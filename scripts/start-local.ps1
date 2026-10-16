# Run from the repository root after following README dependency setup.
$ErrorActionPreference = 'Stop'
$continuumRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $continuumRoot
& '.\.venv\Scripts\python.exe' -m backend.seed
if ($LASTEXITCODE -ne 0) { throw 'Could not seed FalkorDB. Start the database first.' }
& '.\.venv\Scripts\python.exe' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
