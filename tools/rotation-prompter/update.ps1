<#
.SYNOPSIS
    Pulls the latest RS3Helper changes and refreshes this tool's
    dependencies.

.DESCRIPTION
    Fetches origin, fast-forwards main if there's nothing local to lose,
    prints what changed, then re-installs requirements.txt in case it
    changed. Your keys.json is untouched -- it's gitignored specifically
    so updates never overwrite your bindings.

.USAGE
    From this folder, in PowerShell:
        powershell -ExecutionPolicy Bypass -File update.ps1
#>

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "== Updating RS3 Rotation Prompter ==" -ForegroundColor Cyan

$repoRoot = & git -C $root rev-parse --show-toplevel 2>$null
if (-not $repoRoot) {
    Write-Host "This folder isn't a git checkout." -ForegroundColor Red
    Write-Host "Re-clone instead: git clone https://github.com/bburge14/RS3Helper.git"
    exit 1
}

Push-Location $repoRoot
try {
    $dirty = git status --porcelain
    if ($dirty) {
        Write-Host "You have local changes in the repo:" -ForegroundColor Yellow
        Write-Host $dirty
        Write-Host "Not touching those -- commit, discard, or stash them first, then re-run." -ForegroundColor Yellow
        exit 1
    }

    git fetch origin --quiet
    $before = git rev-parse HEAD
    $behindCount = (git rev-list HEAD..origin/main --count).Trim()

    if ($behindCount -eq "0") {
        Write-Host "Already up to date."
    } else {
        Write-Host "Pulling $behindCount new commit(s)..."
        git pull --ff-only origin main
        $after = git rev-parse HEAD
        Write-Host ""
        Write-Host "Changes:" -ForegroundColor Cyan
        git log --oneline "$before..$after"
    }
} finally {
    Pop-Location
}

# Re-install in case requirements.txt changed
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    Write-Host ""
    Write-Host "Refreshing dependencies..."
    & $venvPython -m pip install -r (Join-Path $root "requirements.txt") --quiet
} else {
    Write-Host "No .venv found here -- run install.ps1 first." -ForegroundColor Yellow
    exit 1
}

# Flag new keys the example file has that keys.json doesn't (new abilities
# added upstream need a binding before autopress will fire on them)
$keysPath = Join-Path $root "keys.json"
$examplePath = Join-Path $root "keys.example.json"
if ((Test-Path $keysPath) -and (Test-Path $examplePath)) {
    $mine = Get-Content $keysPath -Raw | ConvertFrom-Json
    $example = Get-Content $examplePath -Raw | ConvertFrom-Json
    $missing = @()
    foreach ($style in $example.PSObject.Properties) {
        if ($style.Name -eq "_comment") { continue }
        $mineStyle = $mine.($style.Name)
        foreach ($ability in $style.Value.PSObject.Properties) {
            if (-not $mineStyle -or -not $mineStyle.PSObject.Properties[$ability.Name]) {
                $missing += "$($style.Name) / $($ability.Name)"
            }
        }
    }
    if ($missing.Count -gt 0) {
        Write-Host ""
        Write-Host "New abilities without a key binding in your keys.json:" -ForegroundColor Yellow
        $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
        Write-Host "Add them manually, or diff against keys.example.json." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Done." -ForegroundColor Green
