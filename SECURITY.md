# Security policy

Do not report real API keys, passwords, access tokens or learner content in a public issue. Rotate any secret that is accidentally exposed.

## Required production controls

- Keep `.env`, keystores and `key.properties` out of Git.
- Use HTTPS only.
- Disable development authentication.
- Use a random JWT secret of at least 32 characters.
- Restrict CORS origins.
- Grant administrator roles only through the backend CLI or a controlled database process.
- Keep admin JWTs tab-scoped for the prototype; do not paste live tokens into issues or saved API collections. A production
  portal should use a hardened session architecture rather than treating browser session storage as a complete XSS defense.
- Use managed PostgreSQL backups.
- Add gateway rate limits and cost alerts for AI requests.
- Define retention/deletion rules for learner text and future audio.
- Never present AI feedback as an official exam result.

The following are prototype boundaries rather than complete production controls:

- development authentication must remain local-only and disabled in production;
- local media storage is not suitable for horizontally scaled deployment;
- Mock AI is suitable for deterministic tests but must be rejected by production configuration;
- the current security policy does not replace a threat model, penetration test or privacy/legal review.

CI audits production Python and Node dependencies. Dependabot also checks Python, Flutter, npm, both Docker images and GitHub Actions dependencies weekly.

The current MVP does not store raw camera images or microphone recordings. OCR is performed on-device and speaking sends only the recognized transcript.
