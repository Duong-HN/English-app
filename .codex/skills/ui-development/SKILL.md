---
name: ui-development
description: "Build, modify, debug, review, or test LearnMate user interfaces across the Flutter mobile app and React administrator dashboard. Use for screens, forms, cards, navigation, dialogs, loading/error/empty states, responsive layouts, Material 3 widgets, admin HTML/CSS, accessibility, keyboard or touch interaction, and UI-focused widget or SSR tests."
---

# UI Development

## Purpose

Create coherent, accessible LearnMate interfaces while preserving each surface's established implementation: Flutter Material 3 for learners and semantic React plus global CSS for administrators.

## When to use

- Add or change a mobile screen/widget under `mobile/lib/src/features/`.
- Add or change administrator markup, controls, tables, dialogs, charts, or responsive behavior.
- Implement loading, empty, error, validation, confirmation, or success feedback.
- Review keyboard, touch, accessibility, overflow, or responsive behavior.
- Add widget or server-rendered UI assertions.

## Project-specific rules

- Select the surface first; do not invent a shared Flutter/React component layer.
- On mobile, use Material 3 from `LearnMateApp`: `ThemeData`, `ColorScheme.fromSeed`, `Scaffold`, `SafeArea`, Material controls, and `Theme.of(context)` typography/colors.
- Preserve mobile navigation through `HomePage`'s `NavigationBar` and `IndexedStack`; tabs keep their state and refresh learning-path/history views when selected.
- Use scrollable content for long learner flows. Follow `AuthPage`'s `SingleChildScrollView` plus `ConstrainedBox(maxWidth: 460)` and `HomePage`'s padded `ListView` patterns.
- Dispose Flutter controllers and services; check `mounted` after asynchronous work before calling `setState`.
- Keep injectable `ApiClient`, `OcrService`, `SpeechService`, and `TokenStore` seams so widget tests can use fakes.
- Use stable `Key` values for interactions that tests must locate, as shown by `learning-path-goal` and `generate-learning-path`.
- On admin web, keep semantic JSX in `app/admin-app.tsx` or `app/api-console.tsx` and static styling in `app/globals.css`.
- Reuse admin CSS variables and existing semantic classes. Inline style is reserved for data-driven dimensions such as trend heights and progress widths.
- Preserve admin breakpoints at 1180, 900, 700, and 440 pixels and the reduced-motion rule.
- Keep browser-only behavior inside client components. The initial server render must still produce the login UI.
- Keep Vietnamese-first user copy and real API data; do not introduce placeholder dashboard records.
- Preserve current accessibility patterns: labels, tooltips, `aria-label`, `aria-live`, alert/status roles, dialog semantics, visible focus, and disabled busy controls.

## Best practices

- Reuse Material widgets and theme values on mobile instead of recreating controls with custom painting.
- Reuse `.panel`, `.metric-card`, button, badge, alert, dialog, pagination, and state-card patterns on admin web.
- Show progress and disable duplicate submission during async actions.
- Design every data view for loading, empty, populated, and failure states.
- Keep destructive actions explicit: confirm first, then report failures with a dialog, alert, message card, or `SnackBar` appropriate to the surface.
- Keep long or dynamic content scrollable and constrain desktop-width forms.
- Use `TextOverflow.ellipsis`, wrapping, or scrolling when backend content may be long.
- Preserve touch targets on mobile and keyboard focus/shortcuts on web.
- Add focused tests using injected fakes or source/SSR assertions rather than live backend, OCR, speech, or AI services.
- Apply `theme-system` for visual-token changes and `localization` for user-facing copy.

## Common mistakes

- Applying web CSS conventions to Flutter or building a cross-platform component abstraction that does not exist.
- Adding Tailwind, CSS Modules, a React component library, or a Flutter UI package for controls already provided by the project.
- Scattering new Flutter colors and text styles instead of using `Theme.of(context)`.
- Replacing `IndexedStack` and accidentally losing tab state.
- Calling `setState` after an async gap without checking `mounted`.
- Forgetting to dispose `TextEditingController` or device services.
- Building fixed-height content that clips Vietnamese text, API errors, or seven-day task details.
- Removing labels/tooltips or relying on color alone for state.
- Making admin dialogs mouse-only or mobile controls keyboard-only.
- Changing strings or widget keys without updating tests.
- Using fake production data to make a screen look complete.

## Required workflow

1. Run `git status --short`; preserve active feature work.
2. Identify mobile, admin, or both, then read the surface's app root, theme source, target widget/component, and focused tests.
3. Trace the real state and API flow before changing markup. List loading, empty, error, success, and destructive states.
4. Reuse existing Material widgets or admin classes and tokens; add a new reusable pattern only when repetition justifies it.
5. Implement semantics, labels/tooltips, disabled/busy behavior, scrolling, overflow handling, and responsive behavior with the feature.
6. Add or update focused tests. Inject mobile fakes; keep admin SSR/source tests aligned with visible copy and integration markers.
7. For mobile changes, run `dart format --output=none --set-exit-if-changed lib test`, `flutter analyze`, and `flutter test` from `mobile/`.
8. For admin changes, run `npm run lint` and `npm test` from `admin-dashboard/`.
9. Perform targeted visual/manual checking when requested or available; do not introduce new browser-test tooling solely for the change.
10. Check the final diff for accidental generated, secret, or unrelated files.

## Examples from this repository

- Mobile composition and Material 3 root: `LearnMateApp` in `mobile/lib/src/app.dart`.
- Responsive authentication form: `AuthPage` uses `SafeArea`, scrolling, a constrained width, themed errors, validation, and busy controls.
- Stateful tab shell: `HomePage` uses `NavigationBar`, selected icons, and `IndexedStack`.
- Rich learner workflow: `_StudyPage` uses Material cards, `SegmentedButton`, text input, OCR/speech actions, and structured result sections.
- Destructive mobile flow: `_HistoryPage._delete()` uses `showDialog`, then `SnackBar` on failure.
- Mobile UI tests: `mobile/test/widget_test.dart` and `mobile/test/home_page_test.dart` use `MemoryTokenStore`, `MockClient`, `FakeOcrService`, and `FakeSpeechService`.
- Admin shell and feature states: `Dashboard`, `UsersPage`, `LearningPathsPage`, dialogs, `LoadingState`, `ErrorState`, and `EmptyState` in `admin-dashboard/app/admin-app.tsx`.
- Admin workbench: `ApiConsole` in `admin-dashboard/app/api-console.tsx` includes keyboard submission and live response announcements.
- Admin responsive/accessibility system: `admin-dashboard/app/globals.css` and `tests/rendered-html.test.mjs`.

## Files to reference

- `mobile/lib/src/app.dart`
- `mobile/lib/src/features/auth/auth_page.dart`
- `mobile/lib/src/features/home/home_page.dart`
- `mobile/test/widget_test.dart`
- `mobile/test/home_page_test.dart`
- `mobile/analysis_options.yaml`
- `admin-dashboard/app/layout.tsx`
- `admin-dashboard/app/page.tsx`
- `admin-dashboard/app/admin-app.tsx`
- `admin-dashboard/app/api-console.tsx`
- `admin-dashboard/app/globals.css`
- `admin-dashboard/tests/rendered-html.test.mjs`
- `admin-dashboard/tests/api-console.test.mjs`

## Files that should never be modified

- Never edit Flutter generated/cache output: `mobile/.dart_tool/`, `mobile/build/`, platform `DerivedData/`, `Pods/`, `.symlinks/`, `GeneratedPluginRegistrant.*`, or generated Flutter ephemeral files.
- Never edit `mobile/android/local.properties`, signing `key.properties`, keystores, or `.jks` files.
- Never hand-edit admin `node_modules/`, `dist/`, `.vinext/`, `.next/`, `.wrangler/`, or `next-env.d.ts`.
- Never hand-edit `mobile/pubspec.lock` or `admin-dashboard/package-lock.json`; update them through package tooling only when dependencies intentionally change.
- Never commit real tokens, passwords, API keys, private learner content, or `.env` secrets.
- Never overwrite unrelated dirty/untracked files.

## Checklist before completion

- [ ] The correct UI surface and its existing patterns were identified.
- [ ] Real state/data flows are preserved; no production mock data was added.
- [ ] Loading, empty, error, success, validation, and destructive states are covered.
- [ ] Layout scrolls, wraps, and responds without clipping likely content.
- [ ] Labels, semantics, focus, tooltips, touch targets, and busy controls are appropriate.
- [ ] Flutter resources are disposed and async `setState` is mounted-safe.
- [ ] Admin server/client boundaries and SSR login output remain valid.
- [ ] Focused mobile/admin tests were updated and the relevant verification commands pass.
- [ ] Generated, secret, and unrelated files are absent from the diff.
