param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile,
    [string]$BackendDirectory = "$(Get-Location)\backend"
)

$ErrorActionPreference = "Stop"

if (-not $env:RESTORE_DATABASE_URL) {
    throw "RESTORE_DATABASE_URL is required and must point to an isolated restore target"
}
if ($env:RESTORE_CONFIRMATION -ne "YES") {
    throw "Set RESTORE_CONFIRMATION=YES only after verifying the target database is disposable"
}

$resolvedBackup = (Resolve-Path -LiteralPath $BackupFile -ErrorAction Stop).Path
& pg_restore --dbname=$env:RESTORE_DATABASE_URL --clean --if-exists --no-owner --no-privileges $resolvedBackup
if ($LASTEXITCODE -ne 0) {
    throw "pg_restore failed with exit code $LASTEXITCODE"
}

$previousDatabaseUrl = $env:DATABASE_URL
$env:DATABASE_URL = $env:RESTORE_DATABASE_URL
Push-Location $BackendDirectory
try {
    & .\.venv\Scripts\python.exe -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        throw "Alembic verification failed with exit code $LASTEXITCODE"
    }
}
finally {
    $env:DATABASE_URL = $previousDatabaseUrl
    Pop-Location
}

Write-Output "Restore drill completed for $resolvedBackup"
