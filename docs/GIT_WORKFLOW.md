# Git workflow

Use short-lived feature branches and pull requests into `main` or `master`. CI must pass before merge.

Commit examples:

```text
feat(auth): add JWT login and secure token storage
feat(ocr): scan Latin text from camera images
test(api): verify per-user history isolation
ci: publish signed APK and backend container on tags
```

Release milestones:

```text
v0.2.0-vertical  text-first prototype
v0.5.0-mvp       auth, OCR, STT, migrations and CI/CD-ready MVP
v0.8.0-rc        user validation, observability and release hardening
v1.0.0           evaluated graduation demo
```

Create releases only from a clean, tested commit:

```powershell
git tag -a v0.5.0-mvp -m "LearnMate authenticated OCR MVP"
git push origin master --follow-tags
```

The tag starts the signed Android release and GHCR backend image workflows.
