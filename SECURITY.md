# Security policy

Do not report real API keys, passwords, access tokens or learner content in a public issue. Rotate any secret that is accidentally exposed.

## Required production controls

- Keep `.env`, keystores and `key.properties` out of Git.
- Use HTTPS only.
- Disable development authentication.
- Use a random JWT secret of at least 32 characters.
- Restrict CORS origins.
- Grant the first administrator role only through the backend CLI. Grant later administrator or teacher roles only through a controlled administrator flow.
- Treat class join codes as rotatable invitations, rate-limit join attempts at the gateway before public launch, and never derive learner or teacher ownership from client-provided IDs.
- Do not expose a learner's private analysis history to a teacher; only assignment submissions are class-visible.
- Pause a teacher's active classes before disabling or changing that account's role; administrator classroom changes are recorded in the audit log.
- Keep teacher/admin web JWTs tab-scoped; do not paste live tokens into issues or saved API collections.
- Use managed PostgreSQL backups.
- Add gateway rate limits and cost alerts for AI requests.
- Define retention/deletion rules for learner text and future audio.
- Never present AI feedback as an official exam result.

CI audits production Python and Node dependencies. Dependabot also checks Python, Flutter, npm, both Docker images and GitHub Actions dependencies weekly.

The current MVP does not store raw camera images or microphone recordings. OCR is performed on-device and speaking sends only the recognized transcript.
