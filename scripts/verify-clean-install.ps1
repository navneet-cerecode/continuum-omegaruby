# Fresh dependencies from the source archive on this machine; not another-machine proof.
$ErrorActionPreference = 'Stop'
$continuumRoot = Split-Path -Parent $PSScriptRoot
$runId = [guid]::NewGuid().ToString('N')
$cleanRoot = Join-Path $continuumRoot ".runtime\clean-$runId"
$cleanGraph = "continuum_clean_$runId"
$python = Join-Path $continuumRoot '.venv\Scripts\python.exe'
$cleanPython = Join-Path $cleanRoot '.venv\Scripts\python.exe'
$priorGraph = $env:FALKORDB_GRAPH
$priorAccess = $env:CONTINUUM_ACCESS
$appProcess = $null
$testedArchiveHash = (Get-FileHash -LiteralPath (Join-Path $continuumRoot 'CONTINUUM-OmegaRuby-source.zip') -Algorithm SHA256).Hash.ToLowerInvariant()
New-Item -ItemType Directory -Path $cleanRoot | Out-Null
Expand-Archive -LiteralPath (Join-Path $continuumRoot 'CONTINUUM-OmegaRuby-source.zip') -DestinationPath $cleanRoot
function Check-Exit([string]$Step) { if ($LASTEXITCODE -ne 0) { throw "Clean install failed at $Step" } }
try {
    & $python -m venv (Join-Path $cleanRoot '.venv'); Check-Exit 'venv'
    Push-Location -LiteralPath $cleanRoot
    try {
        New-Item -ItemType Directory -Force -Path '.runtime' | Out-Null
        & $cleanPython -m pip install -r requirements.lock.txt; Check-Exit 'locked Python dependencies'
        & npm.cmd --prefix frontend ci; Check-Exit 'locked frontend dependencies'
        & npm.cmd --prefix frontend run build; Check-Exit 'production build'
        $env:FALKORDB_GRAPH = $cleanGraph
        $env:CONTINUUM_ACCESS = 'demo'
        Copy-Item -LiteralPath '.env.example' -Destination '.env'
        & $cleanPython -m backend.seed; Check-Exit 'fresh graph seed'
        & $cleanPython -m pytest tests/test_api.py tests/test_release.py -q --basetemp=.runtime/pytest-clean --junitxml=artifacts/pytest-clean.xml; Check-Exit 'API and release regressions'
        $appProcess = Start-Process -FilePath $cleanPython -ArgumentList @('-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8002') -WorkingDirectory $cleanRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $cleanRoot 'app.log') -RedirectStandardError (Join-Path $cleanRoot 'app-error.log')
        $health = $null
        for ($attempt = 0; $attempt -lt 20; $attempt++) {
            try { $health = Invoke-RestMethod 'http://127.0.0.1:8002/api/health' -TimeoutSec 2; break } catch { Start-Sleep -Milliseconds 500 }
        }
        if ($health.database -ne 'available') { throw 'Fresh archive backend did not become available' }
        $html = Invoke-WebRequest 'http://127.0.0.1:8002/' -TimeoutSec 5
        if ($html.StatusCode -ne 200 -or $html.Content -notmatch '/assets/') { throw 'Fresh production UI was not served' }
        Copy-Item -LiteralPath 'artifacts/pytest-clean.xml' -Destination (Join-Path $continuumRoot 'artifacts/pytest-clean.xml')
        [ordered]@{ verified_at = [DateTime]::UtcNow.ToString('o'); passed = $true; source_archive = 'CONTINUUM-OmegaRuby-source.zip'; tested_archive_sha256 = $testedArchiveHash; graph = $cleanGraph; fresh_python_environment = $true; npm_ci = $true; production_build = $true; api_release_tests = $true; http_backend_and_ui = $true; another_machine = $false; docker_execution = $false; limits = 'Same Windows machine, shared existing WSL FalkorDB service, cached dependency downloads may be used. No Docker or other-machine claim.' } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $continuumRoot 'artifacts/release-clean-install.json') -Encoding utf8
    } finally { Pop-Location }
} finally {
    if ($null -ne $appProcess -and -not $appProcess.HasExited) { Stop-Process -Id $appProcess.Id }
    if ($env:FALKORDB_GRAPH -eq $cleanGraph -and $cleanGraph -match '^continuum_clean_[a-f0-9]{32}$' -and (Test-Path -LiteralPath $cleanPython)) {
        Push-Location -LiteralPath $cleanRoot
        try { & $cleanPython -c "from backend.graph import Store; s=Store(); s.revision(); s.graph.delete()" } finally { Pop-Location }
    }
    $env:FALKORDB_GRAPH = $priorGraph
    $env:CONTINUUM_ACCESS = $priorAccess
}
