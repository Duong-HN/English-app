# Git workflow

Use short-lived feature branches and pull requests into `main` or `master`. CI must pass before merge.

Commit examples:

```text
feat(auth): add JWT login and secure token storage
feat(ocr): scan Latin text from camera images
test(api): verify per-user history isolation
ci: publish signed APK and backend container on tags
feat(admin): add operational dashboard and API console
```

Release milestones:

```text
v0.2.0-vertical  text-first prototype
v0.5.0-mvp       auth, OCR, STT, migrations and CI/CD-ready MVP
v0.6.0-admin     RBAC, admin dashboard, API Console and three-service delivery
v0.7.0-paths     personalized learning paths and local-readiness integration
v0.8.0-rc        user validation, observability and release hardening
v1.0.0           evaluated graduation demo
```

Create releases only from a clean, tested commit:

```powershell
git tag -a v0.6.0-admin -m "LearnMate administrator operations release"
git push origin main --follow-tags
```

The tag starts the signed Android release plus GHCR backend/admin image workflows, then invokes configured deployment hooks.
