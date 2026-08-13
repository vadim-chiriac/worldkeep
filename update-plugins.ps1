param(
    [switch]$Check
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $PSScriptRoot "src\runtime\run-python.ps1"
$orchestrator = Join-Path $PSScriptRoot "update_plugins.py"

if (-not (Test-Path -LiteralPath $runner -PathType Leaf)) {
    throw "Bundled Python launcher not found: $runner"
}

$orchestratorArgs = @($orchestrator)
if ($Check) {
    $orchestratorArgs += "--check"
}

& $runner @orchestratorArgs
exit $LASTEXITCODE
