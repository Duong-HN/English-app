param(
    [string]$OutputDirectory = "$(Get-Location)\backups"
)

$ErrorActionPreference = "Stop"

if (-not $env:DATABASE_URL) {
    throw "DATABASE_URL is required"
}

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupFile = Join-Path $OutputDirectory "learnmate-$timestamp.dump"

& pg_dump --dbname=$env:DATABASE_URL --format=custom --no-owner --no-privileges --file=$backupFile
if ($LASTEXITCODE -ne 0) {
    throw "pg_dump failed with exit code $LASTEXITCODE"
}

$hash = Get-FileHash -Algorithm SHA256 -LiteralPath $backupFile
$manifestFile = "$backupFile.sha256"
"$($hash.Hash)  $([IO.Path]::GetFileName($backupFile))" | Set-Content -LiteralPath $manifestFile -Encoding utf8
Write-Output "Created $backupFile"
Write-Output "Created $manifestFile"
