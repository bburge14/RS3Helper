<#
.SYNOPSIS
    Copies your own ability icon PNGs into this app's icons/ folder,
    renaming them to match ability names (underscores -> spaces).

.DESCRIPTION
    Point this at the folder that contains your Mage/Melee/Necro/Range
    subfolders (wherever that sits on your PC -- Downloads, Desktop,
    wherever you had it before uploading to GitHub). It copies every
    .png from those subfolders into icons/, replacing underscores in
    the filename with spaces so they match the ability names the app
    looks up (e.g. Touch_of_Death.png -> Touch of Death.png).

    Doesn't touch GitHub, doesn't touch the repo -- purely a local file
    copy from wherever you point it to this app's (gitignored) icons/
    folder.

.USAGE
    From this folder, in PowerShell:
        powershell -ExecutionPolicy Bypass -File import-icons.ps1 -Source "C:\path\to\RS3Helper"

    If you don't know the path, drag the folder onto PowerShell after
    typing the command above with a trailing space, or just run it with
    no -Source and it'll ask.
#>

param(
    [string]$Source
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$destDir = Join-Path $root "icons"

if (-not $Source) {
    $Source = Read-Host "Path to the folder containing Mage/Melee/Necro/Range"
}
$Source = $Source.Trim('"')

if (-not (Test-Path $Source)) {
    Write-Host "Can't find: $Source" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $destDir)) {
    New-Item -ItemType Directory -Path $destDir | Out-Null
}

$pngs = Get-ChildItem -Path $Source -Recurse -Filter "*.png"
if ($pngs.Count -eq 0) {
    Write-Host "No .png files found under $Source" -ForegroundColor Yellow
    exit 1
}

$copied = 0
foreach ($f in $pngs) {
    $newName = $f.BaseName -replace "_", " "
    $destPath = Join-Path $destDir "$newName.png"
    Copy-Item -Path $f.FullName -Destination $destPath -Force
    Write-Host "  $($f.Name)  ->  icons\$newName.png"
    $copied++
}

Write-Host ""
Write-Host "Copied $copied icon(s) into $destDir" -ForegroundColor Green
Write-Host "Restart RS3 Companion to see them (icons are cached in memory while it's running)."
