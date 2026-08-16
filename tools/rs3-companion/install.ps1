<#
.SYNOPSIS
    Installer for RS3 Companion.

.DESCRIPTION
    Finds a Python interpreter, creates an isolated virtual environment
    in this folder, installs requirements.txt into it, and drops a
    desktop shortcut that launches the app without a console window.

    Updates are handled inside the app itself (Settings tab -> Updates),
    not by a separate script -- run this installer once, then use the
    app's "Check for updates" / "Update now" buttons going forward.

.USAGE
    From this folder, in PowerShell:
        powershell -ExecutionPolicy Bypass -File install.ps1

    If Windows blocks the script outright, right-click install.ps1 ->
    Properties -> check "Unblock" -> OK, then run the command above.
#>

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "== RS3 Companion installer ==" -ForegroundColor Cyan

# 1. Find a Python interpreter
$candidates = @(
    @{ Exe = "py"; Args = @("-3") },
    @{ Exe = "python"; Args = @() },
    @{ Exe = "python3"; Args = @() }
)
$chosen = $null
foreach ($c in $candidates) {
    if (Get-Command $c.Exe -ErrorAction SilentlyContinue) { $chosen = $c; break }
}
if (-not $chosen) {
    Write-Host "Python 3 wasn't found on PATH." -ForegroundColor Red
    Write-Host "Install it from https://www.python.org/downloads/ -- on the first" -ForegroundColor Red
    Write-Host "installer screen, check 'Add python.exe to PATH' -- then re-run this script." -ForegroundColor Red
    exit 1
}
Write-Host "Found Python: $($chosen.Exe) $($chosen.Args -join ' ')"

# 2. Create a virtual environment scoped to this tool
$venvPath = Join-Path $root ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment in .venv ..."
    & $chosen.Exe @($chosen.Args + @("-m", "venv", $venvPath))
} else {
    Write-Host "Virtual environment already exists, reusing it."
}

$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvPythonw = Join-Path $venvPath "Scripts\pythonw.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Virtual environment creation failed -- $venvPython not found." -ForegroundColor Red
    exit 1
}

# 3. Install dependencies
Write-Host "Installing dependencies (this pulls in a GUI toolkit, may take a minute)..."
& $venvPython -m pip install --upgrade pip --quiet
& $venvPython -m pip install -r (Join-Path $root "requirements.txt")

# 4. Write a console launcher (handy for seeing errors)
$runScript = Join-Path $root "run.ps1"
@"
# Launches RS3 Companion with a visible console -- useful for debugging.
& "$venvPython" "$root\app.py"
"@ | Set-Content -Path $runScript -Encoding UTF8
Write-Host "Wrote run.ps1 (console launcher, shows errors)."

# 5. Desktop shortcut -> silent launch via pythonw (no console window)
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "RS3 Companion.lnk"
$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $venvPythonw
$shortcut.Arguments = "`"$root\app.py`""
$shortcut.WorkingDirectory = $root
$shortcut.IconLocation = $venvPythonw
$shortcut.Description = "RS3 Companion -- bar builder, practice/autopress, settings"
$shortcut.Save()
Write-Host "Created desktop shortcut: $shortcutPath"

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "Launch it from the desktop shortcut, or 'powershell -File run.ps1' for a debug console."
Write-Host "Set your key bindings in the app's Settings tab before arming autopress (F8)."
Write-Host "If hotkeys don't register while the game has focus, re-run the shortcut as Administrator"
Write-Host "(right-click the shortcut -> Run as administrator) -- this is a common Windows restriction"
Write-Host "when the game window is itself elevated."
