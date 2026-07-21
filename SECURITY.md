# Security policy

Do not report real API keys, passwords, access tokens or learner content in a public issue. Rotate any secret that is accidentally exposed.

## Required production controls

- Keep `.env`, keystores and `key.properties` out of Git.
- Use HTTPS only.
- Disable development authentication.
- Use a random JWT secret of at least 32 characters.
- Restrict CORS origins.
- Use managed PostgreSQL backups.
- Add gateway rate limits and cost alerts for AI requests.
- Define retention/deletion rules for learner text and future audio.
- Never present AI feedback as an official exam result.

CI audits production Python dependencies against the Python Packaging Advisory Database. Dependabot also checks Python, Flutter, Docker and GitHub Actions dependencies weekly.

The current MVP does not store raw camera images or microphone recordings. OCR is performed on-device and speaking sends only the recognized transcript.
