[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string] $Script,

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]] $ScriptArgs,

    [Parameter(ValueFromPipeline = $true)]
    [AllowNull()]
    [object] $InputObject
)

begin {
    $pipelineInput = [System.Collections.Generic.List[object]]::new()
}

process {
    $pipelineInput.Add($InputObject)
}

end {
    $ErrorActionPreference = "Stop"
    $env:PYTHONDONTWRITEBYTECODE = "1"

    if (-not [System.IO.Path]::IsPathRooted($Script)) {
        $Script = Join-Path $PSScriptRoot $Script
    }
    $Script = [System.IO.Path]::GetFullPath($Script)
    if (-not (Test-Path -LiteralPath $Script -PathType Leaf)) {
        Write-Error "Bundled script not found: $Script"
        exit 2
    }

    $candidates = [System.Collections.Generic.List[object]]::new()

    if ($env:WORLDBUILDING_PYTHON) {
        $candidates.Add([pscustomobject]@{
            Path = $env:WORLDBUILDING_PYTHON
            PrefixArgs = @()
        })
    }

    $workspacePython = Join-Path (Get-Location).Path ".venv\Scripts\python.exe"
    $candidates.Add([pscustomobject]@{ Path = $workspacePython; PrefixArgs = @() })

    $profilePath = [Environment]::GetFolderPath("UserProfile")
    if (-not $profilePath) {
        $profilePath = $env:USERPROFILE
    }
    if ($profilePath) {
        $primaryRuntime = Join-Path $profilePath ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
        $candidates.Add([pscustomobject]@{ Path = $primaryRuntime; PrefixArgs = @() })

        $runtimeRoot = Join-Path $profilePath ".cache\codex-runtimes"
        if (Test-Path -LiteralPath $runtimeRoot -PathType Container) {
            Get-ChildItem -LiteralPath $runtimeRoot -Directory -ErrorAction SilentlyContinue |
                ForEach-Object {
                    $candidatePath = Join-Path $_.FullName "dependencies\python\python.exe"
                    $candidates.Add([pscustomobject]@{ Path = $candidatePath; PrefixArgs = @() })
                }
        }
    }

    foreach ($commandName in @("python3.exe", "python.exe", "py.exe")) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($command -and $command.Source -notlike "*\WindowsApps\*") {
            $prefix = if ($commandName -eq "py.exe") { @("-3") } else { @() }
            $candidates.Add([pscustomobject]@{ Path = $command.Source; PrefixArgs = $prefix })
        }
    }

    $selected = $null
    $seen = @{}
    foreach ($candidate in $candidates) {
        if (-not $candidate.Path -or $seen.ContainsKey($candidate.Path)) {
            continue
        }
        $seen[$candidate.Path] = $true
        if (-not (Test-Path -LiteralPath $candidate.Path -PathType Leaf)) {
            continue
        }
        $probeArgs = @($candidate.PrefixArgs) + @("-c", "import sys")
        & $candidate.Path @probeArgs *> $null
        if ($LASTEXITCODE -eq 0) {
            $selected = $candidate
            break
        }
    }

    if (-not $selected) {
        Write-Error "The bundled canon tools could not find a usable Python runtime."
        exit 127
    }

    $invokeArgs = @($selected.PrefixArgs) + @($Script) + @($ScriptArgs)
    if ($MyInvocation.ExpectingInput) {
        $pipelineInput | & $selected.Path @invokeArgs
    } else {
        & $selected.Path @invokeArgs
    }
    exit $LASTEXITCODE
}
