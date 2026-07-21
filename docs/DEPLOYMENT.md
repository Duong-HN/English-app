# Deployment and CI/CD

## CI

`.github/workflows/ci.yml` runs on pushes and pull requests:

- backend Ruff, pytest and clean Alembic migration;
- Flutter format, analyze, test and Android debug build;
- GitHub Actions syntax, expression and shell validation with actionlint;
- backend Docker image build;
- debug APK artifact retained for 14 days.

## Release

Tags matching `v*` start `.github/workflows/release.yml`:

- verifies Flutter tests;
- builds a signed release APK;
- creates a GitHub Release with the APK;
- pushes backend images to `ghcr.io/<owner>/<repo>/api:<tag>` and `latest`.

Required repository secrets:

```text
ANDROID_KEYSTORE_BASE64
ANDROID_KEYSTORE_PASSWORD
ANDROID_KEY_ALIAS
ANDROID_KEY_PASSWORD
```

Generate an upload key locally with Android `keytool`, Base64-encode the `.jks`, and store only the encoded value in GitHub secrets. Never commit the keystore or `android/key.properties`.

Without `android/key.properties`, a local `flutter build apk --release` uses the debug key only for a release-mode smoke build. Do not distribute that artifact. The GitHub release job fails early unless all real signing secrets are present.

## Backend CD

Configure a GitHub `production` environment and the optional secret:

```text
BACKEND_DEPLOY_HOOK_URL
```

Publishing a GitHub Release invokes this hook. Point it to a managed container platform deployment hook. The platform must run the published image with:

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

The container runs `alembic upgrade head` before Uvicorn and exposes `/health/ready` for health checks.

## What cannot be automated from this local repository

- Creating the GitHub repository/remote without the owner's account choice.
- Creating paid cloud resources or PostgreSQL credentials.
- Uploading Gemini and signing secrets.
- App Store/Play Store publication and legal/privacy declarations.
