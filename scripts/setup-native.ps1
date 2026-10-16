param([switch]$SkipInstall)
$ErrorActionPreference = 'Stop'
$continuumRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $continuumRoot
New-Item -ItemType Directory -Force -Path '.runtime' | Out-Null
function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Setup command failed: $Executable" }
}
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) { Invoke-Checked -Executable 'py' -Arguments @('-3.12','-m','venv','.venv') }
if (-not $SkipInstall) {
    Invoke-Checked -Executable '.venv\Scripts\python.exe' -Arguments @('-m','pip','install','-r','requirements.lock.txt')
    Invoke-Checked -Executable 'npm.cmd' -Arguments @('--prefix','frontend','ci')
}
Invoke-Checked -Executable 'npm.cmd' -Arguments @('--prefix','frontend','run','build')
Invoke-Checked -Executable '.venv\Scripts\python.exe' -Arguments @('-m','backend.seed')
Write-Host 'Setup complete. Run scripts/start-local.ps1. Configure accounts before sharing access; the default is a loopback synthetic demo.'
