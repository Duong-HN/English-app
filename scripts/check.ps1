$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param([scriptblock]$Command)

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE"
    }
}

Push-Location $PSScriptRoot\..
try {
    Invoke-Checked { dart format --output=none --set-exit-if-changed lib test }
    Invoke-Checked { flutter analyze }
    Invoke-Checked { flutter test }

    Push-Location backend
    try {
        Invoke-Checked { & .\.venv\Scripts\python.exe -m ruff format --check app tests alembic }
        Invoke-Checked { & .\.venv\Scripts\python.exe -m ruff check app tests alembic }
        Invoke-Checked { & .\.venv\Scripts\python.exe -m pytest -q }
    }
    finally {
        Pop-Location
    }

    Push-Location admin-web
    try {
        Invoke-Checked { npm run lint }
        Invoke-Checked { npm test }
    }
    finally {
        Pop-Location
    }
}
finally {
    Pop-Location
}
