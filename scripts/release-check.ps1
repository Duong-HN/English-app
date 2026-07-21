$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param([scriptblock]$Command)

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE"
    }
}

$root = (Resolve-Path "$PSScriptRoot\..").Path
Push-Location $root
try {
    Invoke-Checked { & .\scripts\check.ps1 }

    Push-Location backend
    try {
        Invoke-Checked { & .\.venv\Scripts\python.exe -m pip_audit --requirement requirements.txt }
    }
    finally {
        Pop-Location
    }

    Push-Location admin-web
    try {
        Invoke-Checked { npm audit --omit=dev --audit-level=high }
    }
    finally {
        Pop-Location
    }

    Invoke-Checked { docker compose config --quiet }
    Invoke-Checked { docker info --format "Docker server {{.ServerVersion}}" }
    Invoke-Checked {
        docker run --rm --volume "${root}:/repo" --workdir /repo rhysd/actionlint:1.7.12 -no-color
    }
    Invoke-Checked { flutter build apk --release }
    Invoke-Checked { docker build --tag learnmate-api:release backend }
    Invoke-Checked { docker build --tag learnmate-admin:release admin-web }
}
finally {
    Pop-Location
}
