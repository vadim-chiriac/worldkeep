[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$launcher = Join-Path $repoRoot "src\runtime\run-python.ps1"
$seed = Join-Path $repoRoot "src\skills\worldbuilding-scribe\assets\seed-world"
$scratch = Join-Path ([System.IO.Path]::GetTempPath()) ("wb-run-python-" + [guid]::NewGuid().ToString("N"))
$world = Join-Path $scratch "world"

try {
    Copy-Item -LiteralPath $seed -Destination $world -Recurse

    $artifact = @{
        id = "entities/pipeline-smoke"
        kind = "entity"
        type = "person"
        name = "Pipeline Smoke"
        body = "Written through PowerShell pipeline input."
    } | ConvertTo-Json -Depth 10

    $output = $artifact | & $launcher apply.py $world --session pipeline-test --status draft 2>&1
    $outputText = $output -join [Environment]::NewLine
    if ($LASTEXITCODE -ne 0) {
        throw "Piped launcher invocation exited ${LASTEXITCODE}:`n$outputText"
    }
    if ($outputText -notmatch "wrote 1 artifact\(s\)") {
        throw "Piped launcher invocation did not report one write:`n$outputText"
    }
    $written = Join-Path $world "entities\pipeline-smoke.md"
    if (-not (Test-Path -LiteralPath $written -PathType Leaf)) {
        throw "Piped launcher invocation did not create $written"
    }

    $index = & $launcher apply.py $world --index 2>&1
    $indexText = $index -join [Environment]::NewLine
    if ($LASTEXITCODE -ne 0) {
        throw "Ordinary launcher invocation exited ${LASTEXITCODE}:`n$indexText"
    }
    if ($indexText -notmatch "entities/pipeline-smoke") {
        throw "Ordinary launcher invocation did not return the written artifact"
    }

    Write-Output "run-python.ps1 pipeline and ordinary invocation tests passed"
}
finally {
    if (Test-Path -LiteralPath $scratch) {
        Remove-Item -LiteralPath $scratch -Recurse -Force
    }
}
