---
name: dependency-injection
description: >-
  Design, extend, debug, review, or test dependency boundaries across LearnMate. Use for Flutter constructor injection of ApiClient, TokenStore, OcrService, SpeechService, or http.Client; React prop injection of configuration, AdminApi, session data, and callbacks; FastAPI Depends chains for settings, database sessions, authentication, and administrator authorization; or backend AI provider/transport substitution. Preserve manual framework-native injection and test seams—no get_it, injectable, Provider, dependency-injector, or service-locator package is installed.
---

# Dependency Injection

## Purpose

Make external services, configuration, authorization, persistence, and side effects replaceable at clear composition boundaries without introducing a container the repository does not use.

## When to use

- Add or replace an API client, token store, device adapter, AI provider, HTTP transport, database session, settings source, or authenticated principal.
- Make Flutter widgets/controllers, React components, or backend services deterministic in tests.
- Change FastAPI dependency chains, session lifetime, authorization, or application composition.
- Review hidden globals, direct plugin/network construction, service locators, or hard-to-test code.

## Project-specific rules

- Flutter uses constructor injection with production defaults at composition boundaries. `LearnMateApp` accepts optional `ApiClient` and `TokenStore`; `HomePage` accepts optional `OcrService` and `SpeechService`.
- Keep small Dart `abstract interface class` seams for storage and device plugins. `ApiClient` injects `http.Client` and `baseUrl`; tests use `MockClient`, `MemoryTokenStore`, and hand-written OCR/speech fakes.
- Create production implementations once at the owning lifecycle boundary and dispose them there. Do not instantiate clients/plugins repeatedly in `build`.
- The admin server component reads `NEXT_PUBLIC_API_BASE_URL` and passes it to `AdminApp`. `Dashboard` constructs one memoized `AdminApi` from the authenticated session and injects it into page components through typed props.
- Keep admin callbacks explicit (`onLogin`, `onLogout`, `onNavigate`) and do not hide session/API dependencies in module globals or React Context without demonstrated cross-tree need.
- FastAPI injection uses `Depends`: `get_settings`, `get_db`, `get_current_user`, and `require_admin`. Route functions must request the dependencies they use rather than opening sessions or decoding JWTs themselves.
- Preserve `get_db` as a yielding dependency that closes every SQLAlchemy session. Never share a request `Session` globally.
- Preserve both authorization branches: a bearer token flows through `get_current_user` to an active database `User`; the gated non-production dev-header branch may create and return a development user before the active-state check. `require_admin` validates the server-loaded role.
- Keep AI substitution behind `AiProvider` and `build_provider(settings)`. `GeminiProvider` accepts an optional `httpx.AsyncBaseTransport`; tests inject `httpx.MockTransport`.
- `get_settings` is `lru_cache`d. Tests that depend on environment configure it before importing the app, as `backend/tests/conftest.py` does, or explicitly clear the cache in a scoped test.
- Do not add `get_it`, `injectable`, Provider-as-DI, a React DI library, or Python `dependency-injector` without an explicit repository-wide migration.

## Best practices

- Inject behavior at I/O boundaries; pass plain values directly when no substitution or lifecycle is needed.
- Depend on the smallest existing protocol/interface, not a large application object.
- Put concrete defaults only in a composition root or factory; keep feature code unaware of secret lookup and platform construction.
- Make ownership explicit: the creator closes/disposes the dependency unless ownership is intentionally transferred.
- Keep security dependencies server-side and composable. Never inject a client-asserted role as authorization truth.
- Use FastAPI dependency overrides only in scoped tests when needed, and restore them after the test; prefer current real test DB/config where it already provides adequate coverage.
- Memoize React object dependencies whose identity drives effects; include all constructor inputs in the dependency list.
- Add contract tests for each new seam using a fake/MockClient/MockTransport rather than real external services.

## Common mistakes

- Constructing `ApiClient`, `AdminApi`, device plugins, DB sessions, or Gemini transports deep inside frequently called UI/render code.
- Adding a service locator that hides ownership and makes tests order-dependent.
- Letting both a parent and child dispose the same injected client, or never disposing an owned dependency.
- Bypassing `get_current_user`/`require_admin`, trusting a browser role, or manually decoding tokens in routers.
- Using one global SQLAlchemy session across requests or closing an injected session inside a route.
- Reading environment variables throughout features instead of through `Settings`/server composition.
- Mutating cached settings between tests without cache isolation.
- Replacing interfaces with plugin-specific types and forcing widget tests onto platform channels.

## Required workflow

1. Inspect `git status --short`; locate the current composition root, consumers, ownership/disposal, and tests for the dependency.
2. Decide whether the value needs injection. Use direct parameters for plain data and an interface/protocol/factory for replaceable behavior.
3. Add the narrowest seam consistent with the current stack: Dart constructor/interface, typed React prop/callback, FastAPI dependency, or Python protocol/factory.
4. Wire the production implementation at `LearnMateApp`/`HomePage`, `page.tsx`/`Dashboard`, `create_app`/router dependency, or `build_provider` as appropriate.
5. Define lifecycle and security semantics: creator disposal, request session cleanup, cached settings behavior, and server-side role validation.
6. Inject a deterministic fake or transport in focused tests; cover failure and cleanup as well as success.
7. Run the affected stack's format/lint/analyze/tests and any integration/build check warranted by the dependency.
8. Review the diff for hidden globals, duplicate construction, stale constructors/props/dependencies, generated files, secrets, and unrelated edits.

## Examples from this repository

- `LearnMateApp` in `mobile/lib/src/app.dart` defaults to `ApiClient()` and `SecureTokenStore()` but accepts replacements for widget tests.
- `ApiClient` in `mobile/lib/src/core/api_client.dart` accepts `http.Client`/`baseUrl`; `mobile/test/api_client_test.dart` injects `MockClient`.
- `HomePage` defaults to `MlKitOcrService`/`DeviceSpeechService`; `mobile/test/home_page_test.dart` injects `FakeOcrService`/`FakeSpeechService`.
- `admin-dashboard/app/page.tsx` injects the environment-derived base URL; `Dashboard` memoizes `AdminApi` and passes it into its page components.
- `backend/app/dependencies.py` composes OAuth, settings, DB, current-user, and admin requirements through `Depends`.
- `backend/app/ai.py` defines `AiProvider`, a settings-driven factory, and transport injection used by `backend/tests/test_ai.py`.

## Files to reference

- `mobile/lib/src/app.dart`
- `mobile/lib/src/core/api_client.dart`, `mobile/lib/src/core/auth_controller.dart`, `mobile/lib/src/core/token_store.dart`, `mobile/lib/src/core/ocr_service.dart`, `mobile/lib/src/core/speech_service.dart`
- `mobile/lib/src/features/home/home_page.dart`
- `mobile/test/api_client_test.dart`, `mobile/test/auth_controller_test.dart`, `mobile/test/home_page_test.dart`, `mobile/test/widget_test.dart`
- `admin-dashboard/app/page.tsx`
- `admin-dashboard/app/admin-app.tsx`, `admin-dashboard/app/api-console.tsx`
- `admin-dashboard/app/lib/api.ts`, `admin-dashboard/tests/*.mjs`
- `backend/app/main.py`, `backend/app/config.py`, `backend/app/db.py`, `backend/app/dependencies.py`
- `backend/app/ai.py`, `backend/app/routers/*.py`
- `backend/tests/conftest.py`, `backend/tests/test_ai.py`, `backend/tests/*.py`

## Files that should never be modified

- Never edit generated Flutter registrants/ephemeral files, Flutter/admin/backend build outputs, dependency caches, coverage, or Python caches.
- Never hand-edit `mobile/pubspec.lock`, `admin-dashboard/package-lock.json`, Flutter metadata, or generated platform dependency files.
- Never edit or commit backend `.env`, local databases, Android signing files, local SDK configuration, API keys, JWT secrets, or deployment credentials.
- Never overwrite unrelated tracked or untracked work while rewiring dependencies.

## Checklist before completion

- [ ] The dependency has a clear composition root, narrow contract, and owner.
- [ ] Production defaults preserve current behavior and no service locator/container was invented.
- [ ] Flutter disposal, React memoization, FastAPI request cleanup, and settings caching are correct.
- [ ] Authentication/authorization remains server-derived and dependency-driven.
- [ ] Tests inject deterministic fakes/transports without real device, network, or external AI calls.
- [ ] Constructor, prop, factory, and `Depends` call sites are all synchronized.
- [ ] Relevant stack checks pass.
- [ ] No generated, secret, unrelated, or user-owned dirty file changed.
