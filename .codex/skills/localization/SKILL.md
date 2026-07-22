---
name: localization
description: "Maintain LearnMate's current Vietnamese-first language conventions across Flutter mobile, the React administrator dashboard, backend AI output, tests, metadata, accessibility labels, dates, and English-learning speech/input behavior. Use for user-facing copy, validation or error messages, locale-sensitive formatting, translation decisions, AI prompt language, speech locale, or any proposal to introduce an i18n framework."
---

# Localization

## Purpose

Keep language behavior consistent with the current product: Vietnamese interface and teaching guidance for Vietnamese learners, English learning content where pedagogically required, and manual in-source strings because no localization framework exists.

## When to use

- Add or edit user-facing copy, validation, errors, labels, tooltips, empty states, confirmations, metadata, or documentation.
- Format dates, times, numbers, scores, durations, or locale-sensitive text.
- Change speech recognition language, English exercise content, AI prompt/output language, or CEFR labels.
- Evaluate or introduce Flutter ARB/gen-l10n, `intl`, next-intl/react-intl, or another localization framework.

## Project-specific rules

- Treat Vietnamese as the current UI language on both applications. Preserve UTF-8 accents and natural Vietnamese wording.
- Admin document metadata declares `<html lang="vi">`, Open Graph locale `vi_VN`, and uses `Intl.DateTimeFormat("vi-VN")` plus Vietnamese weekday formatting.
- Mobile strings are hard-coded in Dart. There is no `flutter_localizations`, `intl`, ARB file, `l10n.yaml`, delegate, or supported-locale list.
- Admin strings are hard-coded in TSX/TypeScript. There is no next-intl, react-intl, locale route, or message catalog.
- Backend HTTP `detail` messages are currently English and may surface through clients. Do not claim they are localized.
- Backend AI prompts deliberately request Vietnamese explanations and seven-day learning paths for Vietnamese learners in `backend/app/ai.py`.
- Keep target-language content distinct from interface language: English submissions, transcripts, rewrites, vocabulary words, endpoint names, JSON keys, provider names, and CEFR levels are not translated.
- Preserve `localeId: 'en_US'` in `mobile/lib/src/core/speech_service.dart`; speech recognition targets the learner's English, not the Vietnamese UI.
- Preserve stable program values such as `reading`, `writing`, `speaking`, `learner`, `admin`, API paths, audit action names, and schema field names. Translate only their displayed labels.
- Mixed technical labels such as API Console, Backend, Provider, JWT, RBAC, Audit, and HTTP are acceptable where the current audience expects them.
- Update exact-text widget and SSR tests whenever visible copy changes deliberately.
- Do not introduce an i18n framework as incidental cleanup. Treat it as a cross-application migration with fallback, extraction, formatting, and test strategy.

## Best practices

- Write concise, action-oriented Vietnamese with consistent terms: `Học viên`, `Quản trị viên`, `Lộ trình`, `Bài phân tích`, `Đăng nhập`, and `Đăng xuất`.
- Keep error copy useful without exposing secrets, raw provider failures, or sensitive learner data.
- Use locale-aware browser formatting where it already exists; keep backend timestamps timezone-aware ISO values at the API boundary.
- Preserve Vietnamese word order around interpolated values and avoid concatenation that makes future extraction difficult.
- Keep accessibility labels and tooltips synchronized with visible actions.
- Review narrow mobile/web layouts after copy grows.
- When adding a new displayed enum value, add a presentation mapping instead of changing the API value.
- If true multilingual support is requested, inventory all strings across Dart, TSX/TS, Python AI prompts/errors, metadata, tests, and docs before selecting tooling.

## Common mistakes

- Translating API field names, endpoint paths, enum values, audit actions, or JSON payload keys.
- Changing English speech recognition to Vietnamese because the surrounding UI is Vietnamese.
- Translating learner submissions, generated rewrite content, or English vocabulary indiscriminately.
- Assuming backend errors are Vietnamese because the UI is Vietnamese.
- Mixing `vi`, `vi-VN`, and `vi_VN` without respecting HTML, JavaScript Intl, and Open Graph formats.
- Removing diacritics, committing mojibake, or relying on a non-UTF-8 shell/editor.
- Adding an ARB/message-catalog package while leaving most strings hard-coded.
- Changing copy without updating widget/SSR assertions or checking layout overflow.
- Translating technical terms inconsistently between mobile, admin, docs, and AI guidance.

## Required workflow

1. Run `git status --short` and preserve current feature work.
2. Classify each string as Vietnamese UI, English learning content, stable machine value, technical label, backend error, or AI instructional output.
3. Search all applications, tests, metadata, docs, and AI prompts for the term before selecting consistent wording.
4. Edit source strings in UTF-8. Keep machine values and API contracts unchanged; add display mappings when needed.
5. For admin date/metadata changes, verify `lang`, `vi-VN`, and `vi_VN` usage in their correct contexts.
6. For speech changes, verify the target language independently of the UI language.
7. Update exact-text tests and any documentation that repeats the changed language.
8. Run Dart formatting/analyze/tests for mobile changes, npm lint/tests for admin changes, and Ruff/pytest for backend changes.
9. Check the diff for mojibake, accidental generated catalogs, secrets, or unrelated files.

## Examples from this repository

- Admin language and metadata: `metadata`, Open Graph `locale`, and `<html lang="vi">` in `admin-dashboard/app/layout.tsx`.
- Admin dates: `formatDate()` and trend weekday formatting in `admin-dashboard/app/admin-app.tsx`.
- Admin displayed enum mappings and Vietnamese states: `navItems`, `readableError`, analysis labels, and `AuditRow` in `admin-app.tsx`.
- Mobile authentication copy and validation: `AuthPage` in `mobile/lib/src/features/auth/auth_page.dart`.
- Mobile learning UI: navigation labels, study modes, learning paths, confirmations, and profile privacy copy in `mobile/lib/src/features/home/home_page.dart`.
- Intentional English speech target: `DeviceSpeechService.start()` in `mobile/lib/src/core/speech_service.dart` uses `en_US`.
- Vietnamese AI teaching output: mock text and Gemini prompts in `backend/app/ai.py`.
- English backend errors: `backend/app/routers/auth.py`, `analyses.py`, `learning_paths.py`, and `admin.py`.
- Copy-sensitive tests: `mobile/test/home_page_test.dart`, `mobile/test/widget_test.dart`, and `admin-dashboard/tests/rendered-html.test.mjs`.

## Files to reference

- `admin-dashboard/app/layout.tsx`
- `admin-dashboard/app/admin-app.tsx`
- `admin-dashboard/app/api-console.tsx`
- `admin-dashboard/app/lib/api.ts`
- `admin-dashboard/tests/rendered-html.test.mjs`
- `mobile/lib/src/features/auth/auth_page.dart`
- `mobile/lib/src/features/home/home_page.dart`
- `mobile/lib/src/core/speech_service.dart`
- `mobile/test/widget_test.dart`
- `mobile/test/home_page_test.dart`
- `backend/app/ai.py`
- `backend/app/routers/`
- `docs/API.md`
- `README.md`

## Files that should never be modified

- Never edit generated Flutter localization output, plugin registrants, caches, or build products if a localization system is added later; regenerate them from source catalogs.
- Never edit admin build output, `.vinext/`, `.wrangler/`, `.next/`, or generated `next-env.d.ts`.
- Never change stable API keys, enum values, audit action identifiers, or database values merely to translate displayed text.
- Never commit `.env` values, JWTs, API keys, learner-private text, or provider secrets into examples or translation catalogs.
- Never overwrite unrelated dirty/untracked files.

## Checklist before completion

- [ ] Every changed string was classified as UI, learning content, machine value, technical label, backend error, or AI output.
- [ ] Vietnamese wording is consistent, accented, UTF-8, and appropriate to the audience.
- [ ] English learning content and `en_US` speech behavior remain intentional.
- [ ] API paths, JSON keys, enum values, audit actions, and provider identifiers are unchanged.
- [ ] HTML/Intl/Open Graph locale forms are correct for their contexts.
- [ ] Accessibility labels, metadata, tests, and repeated documentation were updated.
- [ ] Long copy was considered on narrow mobile and admin layouts.
- [ ] No partial or nonexistent i18n framework was assumed.
- [ ] Relevant mobile, admin, or backend verification commands pass.
- [ ] No mojibake, secrets, generated output, or unrelated changes are present.
