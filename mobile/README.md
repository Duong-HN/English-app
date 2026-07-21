# LearnMate Mobile

Flutter application for learner registration, authentication, camera/gallery
OCR, English speech-to-text, AI-assisted reading/writing/speaking feedback and
personal learning history.

## Run locally

From this directory:

```powershell
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000
```

Camera OCR and microphone capture require an Android or iOS target. Android
emulators use `http://10.0.2.2:8000` by default. For a physical device, pass the
development computer's LAN address with `--dart-define=API_BASE_URL=...`.

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
