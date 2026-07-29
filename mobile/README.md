# LearnMate Mobile

Flutter application for learner registration, authentication, camera/gallery
OCR, English speech-to-text, AI-assisted reading/writing/speaking feedback,
personalized seven-day learning paths and personal learning history.

## Run locally

From this directory:

```powershell
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000
```

Camera OCR and microphone capture require an Android or iOS target. Android
emulators use `http://10.0.2.2:8000` by default. For a physical device, pass the
development computer's LAN address with `--dart-define=API_BASE_URL=...`.

Approved teachers can open the web Teacher Dashboard from mobile Teacher mode.
Pass its URL at build/run time; use a LAN address when testing on a physical
phone:

```powershell
flutter run -d chrome `
  --dart-define=API_BASE_URL=http://localhost:8000 `
  --dart-define=TEACHER_DASHBOARD_URL=http://localhost:3000
```

Staging and production builds must provide an HTTPS `TEACHER_DASHBOARD_URL`.
The mobile app opens the dashboard in the external browser and does not put a
mobile JWT or other credential in the URL.

The speaking flow grades transcript content, grammar and vocabulary. It does not
claim to grade pronunciation from speech-to-text. The learning-path tab combines
the learner's goal, CEFR level, available daily time and recent backend history.

## Quality checks

```powershell
dart format --output=none --set-exit-if-changed lib test
flutter analyze
flutter test
```

## Build Android

```powershell
flutter build apk --debug
flutter build apk --release
```

A distributable release must be signed with the upload keystore configured in
`android/key.properties`. The repository never stores signing credentials.
