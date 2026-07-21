# LearnMate AI backend

FastAPI backend for the MVP. It uses SQLite and Mock AI by default, so the complete vertical slice can run without an API key.

## Run locally

```powershell
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

OpenAPI is available at <http://127.0.0.1:8000/docs>.

## Use Gemini

Set `AI_PROVIDER=gemini` and `GEMINI_API_KEY` in `.env`. The mobile app never receives the key; only this backend calls the provider. Keep `mock` for automated tests and demos that must not incur API costs.

## Test

```powershell
pytest -q
```
