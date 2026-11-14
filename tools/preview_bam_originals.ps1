# BAM local-only original asset preview (Windows PowerShell 5.1 compatible).
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\preview_bam_originals.ps1 -Catalog
# Keep this file ASCII: Windows PowerShell 5.1 may read BOM-less UTF-8 as ANSI.
param(
    [ValidatePattern('^[0-9]+$')]
    [string]$ResourceId = "1000",
    [ValidateSet("golem","guardian","hunter","channeler","soldier",
                 "raider","brute","boss","forge","barracks","altar")]
    [string]$Role = "raider",
    [ValidatePattern('^[0-9]+$')]
    [string]$PaletteId = "100",
    [switch]$Catalog
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $ani = Join-Path $root "DATA\$ResourceId.ANI"
    $pal = Join-Path $root "DATA\$PaletteId.PAL"
    if (-not (Test-Path -LiteralPath $ani)) {
        throw "Animation file not found: $ani"
    }
    if (-not (Test-Path -LiteralPath $pal)) {
        throw "Palette file not found: $pal"
    }

    if ($Catalog) {
        & python .\tools\bam_assets.py catalog DATA --palette $pal --output .local\bam-assets\catalog
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to build ANI catalog (exit code $LASTEXITCODE)"
        }
        Start-Process .\.local\bam-assets\catalog\catalog.html
    }

    & python .\tools\bam_assets.py extract $ani --palette $pal --output ".local\bam-assets\$ResourceId"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to extract ANI frames (exit code $LASTEXITCODE)"
    }

    & python .\tools\bam_assets.py bind --assets .local\bam-assets --game battle-lab --output .local\bam-assets\asset-pack.js --map "$Role=$ResourceId"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to bind sprite pack (exit code $LASTEXITCODE)"
    }

    Write-Host "Local asset pack ready: $Role -> $ResourceId" -ForegroundColor Green
    Write-Host "In Battle Lab, click the button to enable local sprites."
    Write-Host "This mapping is experimental; original unit identity is not confirmed."
    Start-Process .\battle-lab\index.html
}
finally {
    Pop-Location
}
