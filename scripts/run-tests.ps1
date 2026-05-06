param(
    [switch]$Coverage,
    [switch]$Integration,
    [string]$IntegrationDatabaseUrl
)

$ErrorActionPreference = "Stop"

$backendRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $backendRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonPath)) {
    throw "Backend virtual environment not found at '$pythonPath'. Create it first with 'python -m venv .venv' and install 'requirements-dev.txt'."
}

$pytestArgs = @("-m", "pytest")

if ($Coverage) {
    $pytestArgs += @("--cov=app", "--cov-report=term-missing")
}

if ($Integration) {
    if ($IntegrationDatabaseUrl) {
        $env:INTEGRATION_DATABASE_URL = $IntegrationDatabaseUrl
    }
    $pytestArgs += @("--run-integration", "-m", "integration")
}

Push-Location $backendRoot
try {
    & $pythonPath @pytestArgs
}
finally {
    Pop-Location
}