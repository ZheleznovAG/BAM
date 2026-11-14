# Локальное исследование оригинальных ресурсов. PNG не сохраняются в Git.
# Запуск: powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\preview_bam_originals.ps1
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
    if (-not (Test-Path -LiteralPath $ani)) { throw "Не найден ресурс: $ani" }
    if (-not (Test-Path -LiteralPath $pal)) { throw "Не найдена палитра: $pal" }

    if ($Catalog) {
        & python .\tools\bam_assets.py catalog DATA --palette $pal --output .local\bam-assets\catalog
        if ($LASTEXITCODE -ne 0) { throw "Не удалось сформировать каталог" }
        Start-Process .\.local\bam-assets\catalog\catalog.html
    }

    & python .\tools\bam_assets.py extract $ani --palette $pal --output ".local\bam-assets\$ResourceId"
    if ($LASTEXITCODE -ne 0) { throw "Не удалось извлечь анимацию" }

    & python .\tools\bam_assets.py bind --assets .local\bam-assets --game battle-lab --output .local\bam-assets\asset-pack.js --map "$Role=$ResourceId"
    if ($LASTEXITCODE -ne 0) { throw "Не удалось назначить спрайт" }

    Write-Host "Локальный набор готов: роль $Role -> анимация $ResourceId" -ForegroundColor Green
    Write-Host "В игре нажмите: Подключить локальные спрайты"
    Write-Host "Назначение роли — эксперимент, не идентификация оригинального персонажа."
    Start-Process .\battle-lab\index.html
}
finally {
    Pop-Location
}
