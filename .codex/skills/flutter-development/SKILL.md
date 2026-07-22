---
name: flutter-development
description: >-
  Implement, debug, review, test, or build LearnMate's Flutter application. Use for Dart changes under mobile/lib or mobile/test, pubspec dependency changes, Android or iOS integration, app startup and lifecycle work, mobile API wiring, Flutter analyzer or test failures, and Android build or release work. Follow the repository's existing Material 3, constructor-injection, ChangeNotifier/setState, package:http, and platform-adapter patterns without inventing state, routing, DI, database, Firebase, localization, or code-generation frameworks.
---

# Flutter Development

## Purpose

Develop the learner application in `mobile/` while preserving its small feature/core architecture, native-device boundaries, backend contracts, and tested Flutter conventions.

## When to use

- Change Dart files, Flutter dependencies, app lifecycle, or mobile platform configuration.
- Add or modify learner features, API-backed screens, authentication, OCR, speech capture, or learning-path UI.
- Diagnose `dart format`, `flutter analyze`, `flutter test`, or Android build failures.
- Review Flutter code for lifecycle, platform, security, or regression risks.

## Project-specific rules

- Use Flutter 3.41.4 stable and Dart 3.11.1, matching `.github/workflows/ci.yml` and `mobile/.metadata`; keep `mobile/pubspec.yaml` compatible with `sdk: ^3.11.1`.
- Keep `mobile/lib/main.dart` minimal. Treat `mobile/lib/src/app.dart` as the composition root, theme owner, and authentication gate.
- Follow the current layout: shared adapters/controllers in `mobile/lib/src/core/`; feature UI in `mobile/lib/src/features/`. Do not describe it as Clean Architecture or add repository/use-case layers without an explicit migration.
- Use existing Flutter state only: `AuthController`/`ChangeNotifier`, `AnimatedBuilder`, widget-local `setState`, and `FutureBuilder`. No Provider, Riverpod, BLoC, GetX, or Redux is installed.
- Continue manual constructor injection. `LearnMateApp` accepts `ApiClient` and `TokenStore`; `HomePage` accepts `OcrService` and `SpeechService` test seams.
- Send backend traffic through `ApiClient`. Preserve `API_BASE_URL` as a compile-time `--dart-define`, the Android-emulator default `http://10.0.2.2:8000`, JSON bodies, Bearer behavior, 30-second timeout, and `ApiException` parsing.
- Treat backend payload keys and results as the current `Map<String, dynamic>` contract. Coordinate any shape change with backend schemas, rendering code, and `MockClient` tests.
- Keep UI chrome in Vietnamese and learning input/transcripts in English. The app has no ARB, localization delegates, `intl`, dark theme, or generated Dart models.
- Regard Android and iOS as device-feature targets and web as a preview. Desktop folders are Flutter scaffolds; OCR explicitly supports only Android/iOS.
- Preserve pre-existing tracked and untracked work. Inspect `git status --short` before editing and never overwrite unrelated changes.

## Best practices

- Prefer small widgets and focused methods; use `const`, `final`, and file-private helpers consistently with existing code.
- Guard asynchronous UI updates with `mounted`; clear loading flags in `finally`; dispose `TextEditingController`, speech, recognizers, and owned clients at their established lifecycle boundary.
- Add an interface or injectable constructor parameter when device/network behavior needs a deterministic fake; do not reach native plugins directly from tests.
- Keep user input editable before submission. Preserve readable Vietnamese validation, offline, and server-error states.
- Update native permissions and Dart capability checks together when adding a device feature.
- Add or update the narrowest unit/widget test alongside behavior. Use `flutter_test`, `http/testing.dart`, `MemoryTokenStore`, or small hand-written fakes rather than adding a mocking package by default.
- Change `mobile/pubspec.yaml`, run `flutter pub get`, and review the resulting `mobile/pubspec.lock`; never hand-edit the lockfile.

## Common mistakes

- Introducing an uninstalled architecture, router, state container, DI container, local database, Firebase SDK, or code generator because it is common in other Flutter apps.
- Hard-coding localhost, a LAN address, an API key, or a production backend URL in Dart.
- Assuming camera OCR works on web/desktop or that speech-to-text can grade pronunciation.
- Reordering `HomePage` tabs without updating `_selectPage`, its `GlobalKey` refresh behavior, and widget tests.
- Removing `mounted` checks, failing to dispose controllers/services, or creating a fresh client on every rebuild.
- Editing generated plugin registrants, build outputs, signing files, or unrelated dirty files.
- Treating a debug-signed release-mode APK as distributable; real releases require CI signing secrets.

## Required workflow

1. Run `git status --short` and inspect the target feature, its tests, `mobile/pubspec.yaml`, and relevant backend contract before designing a change.
2. Identify ownership: composition root, core adapter/controller, feature widget, or native platform configuration.
3. Reuse current interfaces and state patterns; justify any new dependency against the absence of an equivalent repository mechanism.
4. Implement the smallest coherent change. Synchronize Dart, native permission/configuration, backend/client contract, and tests when applicable.
5. Run `dart format --output=none --set-exit-if-changed lib test` from `mobile/`; if it reports changes needed, run `dart format lib test` and review only the intended diff.
6. Run `flutter analyze` and `flutter test`. Run the focused test first while iterating, then the full suite.
7. For Android configuration or plugin changes, run at least `flutter build apk --debug`; use the signed release workflow for distributable artifacts.
8. Recheck `git status --short` and `git diff --check`; confirm no generated, secret, or unrelated file was touched.

## Examples from this repository

- `LearnMateApp` in `mobile/lib/src/app.dart` creates `AuthController` once, injects an optional `ApiClient`/`TokenStore`, observes it with `AnimatedBuilder`, and disposes it.
- `HomePage` in `mobile/lib/src/features/home/home_page.dart` injects `OcrService` and `SpeechService`, keeps four tabs alive with `IndexedStack`, and uses private stateful feature widgets.
- `ApiClient` in `mobile/lib/src/core/api_client.dart` injects `http.Client`; `mobile/test/api_client_test.dart` verifies exact URLs, auth headers, JSON, and errors with `MockClient`.
- `mobile/test/home_page_test.dart` implements `FakeOcrService` and `FakeSpeechService` so widget tests never invoke camera or microphone plugins.
- `mobile/android/app/build.gradle.kts` pins minSdk 24, Java 17, release signing behavior, and project-specific R8 rules.

## Files to reference

- `mobile/README.md`
- `mobile/pubspec.yaml`, `mobile/pubspec.lock`, `mobile/analysis_options.yaml`, `mobile/.metadata`
- `mobile/lib/main.dart`, `mobile/lib/src/app.dart`
- `mobile/lib/src/core/*.dart`
- `mobile/lib/src/features/auth/auth_page.dart`
- `mobile/lib/src/features/home/home_page.dart`
- `mobile/test/*.dart`
- `mobile/android/app/build.gradle.kts`, `mobile/android/app/src/main/AndroidManifest.xml`, `mobile/android/app/proguard-rules.pro`
- `mobile/ios/Runner/Info.plist`
- `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `scripts/check.ps1`, `docs/TEST_PLAN.md`

## Files that should never be modified

- Never hand-edit `mobile/.metadata`, `mobile/pubspec.lock`, `.flutter-plugins-dependencies`, or any generated `generated_plugin_registrant*`, `generated_plugins.cmake`, or `GeneratedPluginRegistrant.swift` file.
- Never edit artifacts under `mobile/.dart_tool/`, `mobile/build/`, `mobile/coverage/`, platform `ephemeral/`, or plugin-symlink directories.
- Never edit or commit `mobile/android/local.properties`, `mobile/android/key.properties`, `mobile/android/app/*.jks`, or `mobile/android/app/*.keystore`.
- Never overwrite unrelated pre-existing modifications or untracked files; limit changes to the requested scope.

## Checklist before completion

- [ ] The change follows the actual feature/core, state, routing, and constructor-injection patterns.
- [ ] API payloads, auth headers, device support, permissions, and product disclaimers remain correct.
- [ ] Controllers, services, and asynchronous callbacks have safe lifecycle handling.
- [ ] Focused tests cover the new behavior without real network/device plugins.
- [ ] Formatting, `flutter analyze`, and the full Flutter test suite pass.
- [ ] An Android debug build passes when dependencies or native configuration changed.
- [ ] No generated, secret, unrelated, or user-owned dirty file changed.
