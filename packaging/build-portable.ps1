param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$buildVenv = Join-Path $repoRoot ".portable-build-venv"
$artifactRoot = Join-Path $repoRoot "artifacts"
$stageRoot = Join-Path $artifactRoot "stage"
$bundleRoot = Join-Path $stageRoot "StakeholderDashboard"
$zipPath = Join-Path $artifactRoot "StakeholderDashboard-windows-x64.zip"

if (-not [Environment]::Is64BitProcess) {
    throw "The portable x64 package must be built from a 64-bit PowerShell and Python installation."
}

Push-Location $repoRoot
try {
    npm.cmd --prefix frontend ci
    npm.cmd --prefix frontend run build

    if (-not (Test-Path -LiteralPath $buildVenv)) {
        python -m venv $buildVenv
    }
    $buildPython = Join-Path $buildVenv "Scripts\python.exe"
    & $buildPython -m pip install --disable-pip-version-check -r backend\requirements.txt -r backend\requirements-portable.txt

    & $buildPython -m PyInstaller --noconfirm --clean `
        --distpath $stageRoot `
        --workpath (Join-Path $artifactRoot "build") `
        packaging\windows-portable.spec

    Copy-Item -LiteralPath packaging\windows\StartDashboard.cmd -Destination $bundleRoot
    Copy-Item -LiteralPath packaging\windows\ValidateData.cmd -Destination $bundleRoot
    Copy-Item -LiteralPath packaging\windows\ImportData.cmd -Destination $bundleRoot
    Copy-Item -LiteralPath packaging\windows\README.txt -Destination $bundleRoot
    New-Item -ItemType Directory -Force -Path (Join-Path $bundleRoot "data") | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $bundleRoot "data\uploads") | Out-Null
    Copy-Item -LiteralPath packaging\windows\import-template.json -Destination (Join-Path $bundleRoot "data\import-template.json")

    $archived = $false
    foreach ($attempt in 1..5) {
        try {
            if (Test-Path -LiteralPath $zipPath) {
                Remove-Item -LiteralPath $zipPath
            }
            Compress-Archive -LiteralPath $bundleRoot -DestinationPath $zipPath -CompressionLevel Optimal
            $archived = $true
            break
        } catch {
            if ($attempt -eq 5) { throw }
            Start-Sleep -Seconds 2
        }
    }
    if (-not $archived) { throw "The portable ZIP could not be created." }
    Write-Host "Portable package created: $zipPath"
} finally {
    Pop-Location
}
