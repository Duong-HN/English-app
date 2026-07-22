---
name: ci-cd-release
description: "Maintain LearnMate continuous integration, Docker/Compose delivery, signed Android releases, GHCR images, Cloudflare/Vinext packaging, deployment hooks, and release readiness. Use for workflow, build, container, artifact, dependency-audit, signing, tag, or deployment automation changes."
---

# CI CD and Release

## Purpose

Keep all three applications reproducibly tested, packaged, published, and deployed as one release unit.

## When to use

Use for `.github/workflows`, Dockerfiles, Compose, build scripts, Sites/Worker packaging, signing, artifacts, GHCR images, deploy hooks, Dependabot, or release checks.

## Project-specific rules

- CI runs on pushes and pull requests to `main`, `master`, and `develop`; preserve least-privilege permissions and workflow concurrency cancellation.
- Backend CI uses Python 3.14, Ruff format/lint, `pip-audit`, pytest, a clean Alembic upgrade, and a container build.
- Flutter CI uses Flutter 3.41.4, format/analyze/tests with coverage, an Android debug APK, and a 14-day artifact.
- Admin CI uses Node 24.14.0, `npm ci`, ESLint, `npm test` (which builds Vinext), production dependency audit, and a container build.
- Validate Actions syntax and shell expressions with actionlint.
- `v*` tags require Android signing secrets, build a signed release APK, publish backend/admin GHCR images, create a GitHub Release, then call the reusable deploy workflow.
- Deployment hooks are optional and environment-scoped. Do not pretend hook invocation provisions infrastructure or credentials.
- Admin is built with Vinext/Vite/Cloudflare Worker semantics. Preserve `admin-dashboard/.openai/hosting.json`, `vite.config.ts`, `worker/index.ts`, and `build/sites-vite-plugin.ts` when working on Sites packaging.
- Production API startup must run `alembic upgrade head` before Uvicorn and use `AUTO_CREATE_SCHEMA=false`.
- A local release build without `mobile/android/key.properties` uses debug signing only as a smoke build; never distribute it.

## Best practices

- Pin action/tool/runtime versions deliberately and update manifests/locks through their package managers.
- Keep CI commands aligned with `scripts/check.ps1`, `scripts/release-check.ps1`, component READMEs, and `docs/DEPLOYMENT.md`.
- Test workflow changes locally where possible: actionlint, Compose config, component build, Docker build.
- Preserve non-root runtime users and health checks in both service images.
- Keep build contexts narrow through `.dockerignore`.
- Separate build/test/publish/deploy jobs so failures stop later irreversible steps.

## Common mistakes

- Adding a check to CI but not the local scripts/documentation, or vice versa.
- Using `pip install`/`npm install` inconsistently with pinned requirements and `npm ci`.
- Publishing an image or release before tests, signing validation, and all artifacts succeed.
- Relying only on a workflow-created `release.published` event instead of the explicit reusable deploy call documented in `docs/DEPLOYMENT.md`.
- Putting secrets in `NEXT_PUBLIC_*`, Compose source, workflow logs, artifacts, or repository files.
- Pointing dashboard public API configuration at an internal Docker hostname.
- Replacing Vinext commands with conventional `next` commands.
- Editing generated `dist`, APK output, or Wrangler state.

## Required workflow

1. Identify the trigger, permissions, environment, artifacts, secrets, and failure boundaries affected.
2. Read the workflow plus the corresponding local script, Dockerfile/Compose config, and deployment docs.
3. Make the smallest workflow/build change with explicit versions and narrow permissions.
4. Run component lint/tests/builds and dependency audits as relevant.
5. Run `docker compose config --quiet`, Docker builds, and actionlint for delivery changes.
6. Verify health checks, non-root users, migration startup, artifact paths, retention, and tag/image names.
7. Verify secrets are referenced only through the approved environment/GitHub mechanisms.
8. Update `docs/DEPLOYMENT.md`, component READMEs, and `CHANGELOG.md` when release behavior changes.

## Examples from this repository

- `.github/workflows/ci.yml` separates workflow lint, backend, Flutter, admin, and two container-build jobs.
- `.github/workflows/release.yml` validates four Android signing secrets before building and publishes API/admin images under separate GHCR suffixes.
- `.github/workflows/deploy.yml` safely skips an unconfigured hook and retries configured POST requests.
- `backend/Dockerfile` migrates before serving as `learnmate`; `admin-dashboard/Dockerfile` builds with Vinext and runs as `node`.
- `scripts/release-check.ps1` composes fast checks, dependency audits, actionlint, release-mode APK, and both images.

## Files to reference

- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`
- `.github/workflows/deploy.yml`
- `.github/dependabot.yml`
- `scripts/check.ps1`
- `scripts/release-check.ps1`
- `docker-compose.yml`
- `backend/Dockerfile`
- `admin-dashboard/Dockerfile`
- `mobile/android/app/build.gradle.kts`
- `docs/DEPLOYMENT.md`

## Files that should never be modified

- Never create or edit real signing keys, `mobile/android/key.properties`, `.jks`/keystore files, `.env` secrets, tokens, or deployment-hook values in the repository.
- Never edit generated APKs, `dist/`, `build/`, `.wrangler/`, caches, or vendor trees.
- Never mutate `.openai/hosting.json` project identity casually; change it only for an explicitly authorized hosting migration.
- Never create/push tags, releases, images, or deployments unless the user requested that external state change.
- Never overwrite unrelated working-tree changes.

## Checklist before completion

- [ ] Trigger, permissions, concurrency, dependencies, and failure ordering are correct.
- [ ] Local and CI commands remain aligned.
- [ ] Component tests, audits, actionlint, Compose, and relevant builds pass.
- [ ] Images run non-root, migrate safely, and expose working health checks.
- [ ] Signing, public URLs, and deployment hooks use secrets safely.
- [ ] Release/deployment docs describe the implemented automation and its manual gaps.
