# Deployment and CI/CD

## Deployment status

The workflows in this document package and verify a graduation-project prototype. A successful CI build or image publish is
not evidence of production readiness. Public deployment additionally requires PostgreSQL integration testing, a separate
migration job, object storage, rate limiting, monitoring, backups, restore testing and a verified rollback procedure.

The staged target architecture and production exit gates are defined in [Production roadmap](PRODUCTION_ROADMAP.md).

## CI

`.github/workflows/ci.yml` runs on pushes and pull requests:

- backend Ruff, pytest and clean Alembic migration;
- admin web ESLint, unit/SSR tests and production build;
- Flutter format, analyze, test and Android debug build;
- GitHub Actions syntax, expression and shell validation with actionlint;
- backend and admin web Docker image builds;
- debug APK artifact retained for 14 days.

## Release

Tags matching `v*` start `.github/workflows/release.yml`:

- verifies Flutter tests;
- builds a signed release APK;
- creates a GitHub Release with the APK;
- pushes backend images to `ghcr.io/<owner>/<repo>/api:<tag>` and `latest`.
- pushes admin images to `ghcr.io/<owner>/<repo>/admin:<tag>` and `latest`.
- invokes the reusable production deployment workflow after release publication.

Required repository secrets:

```text
ANDROID_KEYSTORE_BASE64
ANDROID_KEYSTORE_PASSWORD
ANDROID_KEY_ALIAS
ANDROID_KEY_PASSWORD
```

Generate an upload key locally with Android `keytool`, Base64-encode the `.jks`, and store only the encoded value in GitHub secrets. Never commit the keystore or `mobile/android/key.properties`.

Without `mobile/android/key.properties`, a local `flutter build apk --release` uses the debug key only for a release-mode smoke build. Do not distribute that artifact. The GitHub release job fails early unless all real signing secrets are present.

## Service CD

Configure a GitHub `production` environment and the optional secret:

```text
BACKEND_DEPLOY_HOOK_URL
ADMIN_DEPLOY_HOOK_URL
```

Publishing a GitHub Release invokes these hooks. Point them to managed container platform deployment hooks. The backend platform must run the published image with:

```text
APP_ENV=production
DATABASE_URL=<managed PostgreSQL URL>
AUTO_CREATE_SCHEMA=false
JWT_SECRET=<32+ random characters>
ENABLE_DEV_AUTH=false
AI_PROVIDER=gemini
GEMINI_API_KEY=<secret>
ALLOWED_ORIGINS=<explicit HTTPS origins>
```

The prototype container runs `alembic upgrade head` before Uvicorn and exposes `/health/ready` for health checks. This
startup-migration pattern is suitable only for a controlled single-instance demonstration. Production deployments should
run migrations as a separate, reviewed job before application rollout.

Run the admin image with:

```text
PORT=3000
NEXT_PUBLIC_API_BASE_URL=<public HTTPS backend URL>
NEXT_PUBLIC_SITE_URL=<public HTTPS administrator URL>
```

The browser, not the container network, calls `NEXT_PUBLIC_API_BASE_URL`; therefore
this must be a public URL and must also appear in backend `ALLOWED_ORIGINS`. The
admin container exposes `/` as its health endpoint and runs as the non-root Node
user.

The deployment workflow is called directly by the tag release workflow. This is
intentional: GitHub events created with the workflow token do not reliably start a
second workflow, so relying only on a `release.published` event would leave an
automation gap. Manual releases and `workflow_dispatch` remain supported.

## Local three-service environment

```powershell
docker compose up --build --wait
```

Expected endpoints:

- `http://localhost:3000` — LearnMate Admin;
- `http://localhost:8000/health/ready` — API readiness;
- `http://localhost:8000/docs` — Swagger UI.

Compose waits for PostgreSQL, migrates the API schema, then starts the admin web
after the API reports healthy.

This Compose environment is for local development and demonstration. It is not a
production topology and does not provide managed backups, multi-instance shared
media, TLS termination, autoscaling or disaster recovery.

## What cannot be automated from this local repository

- Creating the GitHub repository/remote without the owner's account choice.
- Creating paid cloud resources or PostgreSQL credentials.
- Uploading Gemini and signing secrets.
- App Store/Play Store publication and legal/privacy declarations.
