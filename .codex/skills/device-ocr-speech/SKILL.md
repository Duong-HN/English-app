---
name: device-ocr-speech
description: >-
  Implement, debug, review, or test LearnMate's camera/gallery OCR and English speech-to-text capture. Use when changing OcrService, MlKitOcrService, SpeechService, DeviceSpeechService, study-mode controls, editable OCR/transcript handoff, image_picker, Google ML Kit text recognition, speech_to_text, Android or iOS permissions, platform support, native release rules, or their fakes and widget tests. Preserve the product boundary that OCR is on-device Latin recognition on Android/iOS and transcript grading covers content, grammar, and vocabulary—not pronunciation.
---

# Device OCR and Speech

## Purpose

Maintain reliable, privacy-conscious device input that converts an image or English speech into user-editable text before the backend performs formative analysis.

## When to use

- Change camera/gallery selection, OCR preprocessing, recognition scripts, or platform support.
- Change microphone permissions, speech recognition options, transcript callbacks, or start/stop behavior.
- Modify reading/speaking controls or the handoff from recognized text to `ApiClient.analyze`.
- Add tests or diagnose plugin, permission, R8, lifecycle, device-only, or platform failures.

## Project-specific rules

- Keep both plugin boundaries behind `OcrService` and `SpeechService` in `mobile/lib/src/core/`; widgets receive the interfaces through `HomePage`.
- Preserve `MlKitOcrService.isSupported`: OCR is allowed only when not web and the target is Android or iOS.
- Keep OCR local. `MlKitOcrService.recognize` picks one image, bounds it with `imageQuality: 90` and `maxWidth: 2048`, uses `TextRecognitionScript.latin`, trims text, and closes `TextRecognizer` in `finally`.
- Preserve both camera and gallery inputs. Cancellation returns `null`; an image with no recognized text is a distinct, readable UI state.
- Preserve Android camera permission and iOS camera/photo usage descriptions. Keep Android minSdk 24 and the deliberate R8 suppressions for unbundled Chinese, Devanagari, Japanese, and Korean recognizers.
- Keep speech recognition configured for English (`en_US`), partial results, cancel-on-error, and dictation mode in `DeviceSpeechService`.
- Stop speech when the learner stops, changes study mode, or the study widget is disposed. Changing tabs currently preserves the study widget inside an `IndexedStack` and does not stop listening by itself. Synchronize `_listening` from service callbacks and guard callbacks with `mounted`.
- Keep recognized OCR text and speech transcripts editable in the same study `TextField` before analysis.
- Never represent speech-to-text as pronunciation or accent assessment. Preserve the visible disclaimer and backend prompt boundary documented in `docs/ARCHITECTURE.md`.
- Do not send raw images or audio to the backend under the current design; only reviewed text goes through `/api/v1/analyses/{type}`.

## Best practices

- Check capability before invoking a device plugin and present a useful unsupported/permission error instead of crashing.
- Request only permissions needed by the selected feature and keep permission copy specific enough for store review.
- Treat plugin callbacks as asynchronous UI input: verify `mounted`, update cursor selection after transcript changes, and prevent concurrent capture/analysis actions.
- Close every per-scan recognizer even when processing throws; keep speech stop idempotent.
- Preserve the interface shape so widget tests can use hand-written fakes without platform channels.
- Test cancellation, empty OCR, permission/unavailable speech, partial transcript, mode changes, and editable handoff when changing those paths.
- Validate on a physical Android device after native/plugin changes; the manual acceptance matrix is in `docs/TEST_PLAN.md`.

## Common mistakes

- Calling `ImagePicker`, `TextRecognizer`, or `SpeechToText` directly inside a widget and losing the test seam.
- Enabling OCR buttons for unsupported platforms without handling `isSupported` or an `UnsupportedError`.
- Adding another ML Kit script dependency while leaving `proguard-rules.pro`, package size, and recognition configuration inconsistent.
- Forgetting Android/iOS permission declarations or changing usage text without testing denial and recovery.
- Replacing the entire transcript on a late callback after the widget is disposed or the learner switches mode.
- Submitting text immediately after OCR/STT and removing the learner's review/edit step.
- Claiming pronunciation scoring from a text transcript or sending raw audio/images without an explicit privacy and backend design change.
- Testing with real plugins or device channels in unit/widget tests.

## Required workflow

1. Inspect `git status --short`, the two service interfaces, `_StudyPageState`, native manifests/plists, dependency versions, and current fakes before editing.
2. Classify the change as service behavior, UI orchestration, native configuration, dependency/R8 work, or backend analysis semantics.
3. Preserve or extend the interface first; add an injectable collaborator when deterministic testing requires it.
4. Implement platform guards, cancellation/error handling, resource cleanup, and editable text handoff together.
5. Synchronize Android permissions/Gradle/R8 and iOS usage descriptions with the exact device behavior.
6. Update `mobile/test/home_page_test.dart` and add focused service tests where logic can run without platform channels.
7. Run Flutter format, analyze, and tests; run `flutter build apk --debug` for plugin/native changes.
8. Perform the relevant physical-device cases from `docs/TEST_PLAN.md:50-60`; record any untestable platform constraint in the handoff.
9. Confirm the transcript-only pronunciation disclaimer, user review step, and no-raw-media boundary remain true.

## Examples from this repository

- `MlKitOcrService` in `mobile/lib/src/core/ocr_service.dart` injects `ImagePicker`, restricts platforms, bounds the image, uses the Latin recognizer, and closes it.
- `_scan` in `mobile/lib/src/features/home/home_page.dart` distinguishes cancellation, empty text, successful editable text, and plugin errors while managing `_capturing`.
- `DeviceSpeechService` in `mobile/lib/src/core/speech_service.dart` translates plugin error/status/result callbacks into the project interface.
- `_toggleSpeech`, `_changeMode`, and `dispose` in `home_page.dart` manage speech lifecycle and keep the transcript cursor at the end.
- `FakeOcrService` and `FakeSpeechService` in `mobile/test/home_page_test.dart` verify that recognized text feeds the editable study field.

## Files to reference

- `mobile/lib/src/core/ocr_service.dart`
- `mobile/lib/src/core/speech_service.dart`
- `mobile/lib/src/features/home/home_page.dart`
- `mobile/test/home_page_test.dart`
- `mobile/pubspec.yaml`, `mobile/pubspec.lock`
- `mobile/android/app/src/main/AndroidManifest.xml`
- `mobile/android/app/build.gradle.kts`, `mobile/android/app/proguard-rules.pro`
- `mobile/ios/Runner/Info.plist`
- `mobile/README.md`
- `docs/ARCHITECTURE.md`, `docs/TEST_PLAN.md`, `SECURITY.md`
- `backend/app/ai.py`, `backend/app/routers/analyses.py`

## Files that should never be modified

- Never hand-edit Flutter-generated plugin registrants, `.flutter-plugins-dependencies`, `mobile/.metadata`, or `mobile/pubspec.lock`.
- Never edit `mobile/.dart_tool/`, `mobile/build/`, platform `ephemeral/`, plugin symlinks, generated Gradle/Xcode output, or coverage artifacts.
- Never edit or commit `mobile/android/local.properties`, `mobile/android/key.properties`, keystores, backend `.env`, or any API/signing secret.
- Never remove unrelated dirty work while changing device files.

## Checklist before completion

- [ ] OCR support, script, image bounds, cancellation, empty result, and recognizer cleanup are correct.
- [ ] Speech locale/options, callbacks, stop behavior, and mounted checks are correct.
- [ ] Android and iOS permissions accurately match behavior.
- [ ] Recognized text remains editable and only text—not raw media—is sent to the backend.
- [ ] The UI and AI prompt do not claim pronunciation assessment.
- [ ] Fakes/tests cover the changed handoff or error path.
- [ ] Flutter format, analyze, tests, and the needed Android/device checks pass.
- [ ] No generated, secret, unrelated, or user-owned dirty file changed.
