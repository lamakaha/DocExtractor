param(
    [Parameter(Position = 0)]
    [ValidateSet("help", "status", "next")]
    [string]$Command = "help"
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$statePath = Join-Path $repoRoot ".planning\STATE.md"
$phaseDir = Join-Path $repoRoot ".planning\phases"

function Get-StateValue {
    param(
        [string]$Label
    )

    if (-not (Test-Path $statePath)) {
        return $null
    }

    $match = Select-String -Path $statePath -Pattern "^- \*\*$Label\*\*: (.+)$" | Select-Object -First 1
    if ($match) {
        return $match.Matches[0].Groups[1].Value.Trim()
    }
    return $null
}

function Get-NextPlanCommand {
    if (-not (Test-Path $phaseDir)) {
        return "gsd-help"
    }

    $planFiles = Get-ChildItem -Path $phaseDir -Recurse -Filter "*-PLAN.md"
    $ids = @()
    foreach ($file in $planFiles) {
        if ($file.BaseName -match "^(\d{2})-(\d{2})-PLAN$") {
            $phase = [int]$matches[1]
            $wave = [int]$matches[2]
            $summaryPath = Join-Path $file.DirectoryName ("{0}-{1}-SUMMARY.md" -f $matches[1], $matches[2])
            $ids += [pscustomobject]@{
                Phase = $phase
                Wave = $wave
                SummaryExists = (Test-Path $summaryPath)
            }
        }
    }

    if (-not $ids) {
        return "gsd-help"
    }

    $latest = $ids | Sort-Object Phase, Wave | Select-Object -Last 1
    if (-not $latest.SummaryExists) {
        return "gsd-continue"
    }

    $nextWave = "{0:D2}" -f ($latest.Wave + 1)
    $phase = "{0:D2}" -f $latest.Phase
    return "gsd-start $phase-$nextWave next-slice"
}

$phase = Get-StateValue -Label "Phase"
$plan = Get-StateValue -Label "Plan"
$nextStep = Get-StateValue -Label "Next Step"
$gitStatus = git status --short 2>$null
$isDirty = [string]::IsNullOrWhiteSpace(($gitStatus | Out-String)) -eq $false
$recommended = Get-NextPlanCommand

switch ($Command) {
    "help" {
        Write-Output "GSD commands:"
        Write-Output "gsd-help"
        Write-Output "gsd-status"
        Write-Output "gsd-next"
        Write-Output "gsd-start <plan-id> <title>"
        Write-Output "gsd-continue"
        Write-Output "gsd-close <plan-id>"
        Write-Output ""
        Write-Output "Current phase: $phase"
        Write-Output "Current plan: $plan"
        if ($nextStep) {
            Write-Output "Planning next step: $nextStep"
        }
        Write-Output "Recommended next command: $recommended"
    }
    "status" {
        Write-Output "Phase: $phase"
        Write-Output "Plan: $plan"
        if ($nextStep) {
            Write-Output "Next step: $nextStep"
        }
        Write-Output "Git dirty: $isDirty"
        if ($isDirty) {
            Write-Output ""
            $gitStatus
        }
    }
    "next" {
        Write-Output $recommended
    }
}
