---
name: theme-system
description: "Maintain or extend LearnMate visual styling across the Flutter Material 3 mobile application and React administrator dashboard. Use for colors, typography, spacing, component appearance, CSS variables, responsive breakpoints, light/dark theme decisions, visual consistency, accessibility contrast, or refactoring duplicated style values."
---

# Theme System

## Purpose

Preserve LearnMate's current light, blue-led visual identity while applying theme changes separately through Flutter `ThemeData` and admin CSS custom properties. No generated or shared cross-platform token system exists.

## When to use

- Change brand colors, surfaces, typography, spacing, elevation, borders, focus, or motion.
- Add a reusable visual variant or remove duplicated style values.
- Review contrast, hierarchy, consistency, dark-mode proposals, or responsive styling.
- Change mobile `ThemeData` or admin `:root` variables and shared CSS classes.

## Project-specific rules

- Treat mobile and admin as two implementations of the same product identity, not one compiled theme package.
- Preserve the common primary blue `#2563EB`: mobile `ColorScheme.fromSeed` in `mobile/lib/src/app.dart` and admin `--blue` in `admin-dashboard/app/globals.css`.
- Mobile currently uses a light Material 3 theme with scaffold `#F8FAFC`, white filled inputs, outlined input borders, and zero-elevation cards.
- Use `Theme.of(context).colorScheme` and `textTheme` in feature widgets. Keep root bootstrap literals in `LearnMateApp`; centralize a new semantic value there before repeating it.
- Prefer Material 3 components (`NavigationBar`, `FilledButton`, `OutlinedButton`, `Card`, `Chip`, `SegmentedButton`) so interaction states derive from the theme.
- Admin tokens live in `:root`: ink, muted, line, surfaces, canvas, navy, blue, green, purple, amber, red, soft variants, and shadow.
- Reuse admin semantic variants such as `.tone-*`, `.status-pill`, `.type-badge`, button variants, alerts, and state cards.
- Keep static admin visuals in `globals.css`. Use inline styles only for computed data values such as chart height or progress width.
- Preserve admin focus visibility and `prefers-reduced-motion` behavior.
- Preserve current admin breakpoints unless a measured layout requirement warrants changing them.
- There is no dark theme, custom font asset, theme switch, or token generator. Do not document or depend on one.
- Theme work must not silently alter Vietnamese content, API state meaning, or accessibility semantics.

## Best practices

- Map a new color to a semantic role before adding a literal.
- Use the Material color scheme for mobile success/error/primary states where possible; use existing soft/status admin variables for web.
- Keep text hierarchy in `textTheme` on mobile and existing heading/body classes/selectors on admin.
- Verify hover, focus, disabled, selected, success, warning, error, and destructive variants together.
- Preserve sufficient text/background contrast and never convey status through color alone.
- Test long Vietnamese labels at narrow widths before tightening spacing or typography.
- Keep visual changes scoped; do not rebrand both applications when only one surface is requested.
- If a future cross-platform token source is requested, design an explicit migration and generation workflow rather than manually pretending values are synchronized.

## Common mistakes

- Scattering `Color(...)`, `Colors.*`, or hex values throughout new Flutter feature widgets.
- Adding a second primary blue instead of using the seed/color scheme or `--blue`.
- Treating admin CSS variables as automatically shared with Flutter.
- Adding Tailwind, CSS-in-JS, a Flutter theming package, or a design-token generator without an explicit need.
- Replacing Material interaction behavior with custom containers and gesture handling.
- Changing only default colors while forgetting selected, disabled, focus, error, and destructive states.
- Adding dark mode without auditing dialogs, forms, charts, cards, overlays, Worker-rendered login HTML, and platform system styling.
- Removing reduced-motion behavior or visible focus outlines for aesthetics.
- Editing the social card or platform icons as an incidental theme change.

## Required workflow

1. Inspect `git status --short` and preserve active work.
2. Read `mobile/lib/src/app.dart` and/or the `:root` plus affected selectors in `admin-dashboard/app/globals.css`.
3. Inventory the semantic role, all interaction states, and every component using the value before changing it.
4. Reuse an existing token or Material role. If none fits and reuse is likely, add one central semantic value rather than repeated literals.
5. Apply the smallest surface-specific change and verify responsive, selected, disabled, focus, success, warning, error, and destructive states.
6. Update focused widget/SSR assertions only when behavior or visible contract changes.
7. For mobile, run Dart formatting, `flutter analyze`, and `flutter test`.
8. For admin, run `npm run lint` and `npm test`.
9. Check the diff for unrelated asset, dependency, generated, or secret changes.

## Examples from this repository

- Mobile root theme: `ThemeData`, `ColorScheme.fromSeed`, `useMaterial3`, `InputDecorationTheme`, and `CardThemeData` in `mobile/lib/src/app.dart`.
- Mobile theme consumption: `Theme.of(context).textTheme` throughout `AuthPage` and `HomePage`; themed error color in `AuthPage`.
- Mobile Material components: `NavigationBar` in `HomePage`, `FilledButton` in `AuthPage`, and cards/chips/segmented controls in the learner flows.
- Admin token source: `:root` in `admin-dashboard/app/globals.css`.
- Admin status hierarchy: `.tone-*`, `.status-pill`, `.type-badge`, `.method-label`, alerts, and response metrics in `globals.css`.
- Admin responsive/motion rules: media queries and `prefers-reduced-motion` at the end of `globals.css`.
- Product social appearance: metadata in `admin-dashboard/app/layout.tsx` references `public/og-learnmate-admin.png`.

## Files to reference

- `mobile/lib/src/app.dart`
- `mobile/lib/src/features/auth/auth_page.dart`
- `mobile/lib/src/features/home/home_page.dart`
- `mobile/pubspec.yaml`
- `admin-dashboard/app/globals.css`
- `admin-dashboard/app/admin-app.tsx`
- `admin-dashboard/app/api-console.tsx`
- `admin-dashboard/app/layout.tsx`
- `admin-dashboard/public/og-learnmate-admin.png`

## Files that should never be modified

- Never edit Flutter caches/build products, generated plugin registrants, `Pods/`, `DerivedData/`, or platform ephemeral files.
- Never edit admin `node_modules/`, `dist/`, `.vinext/`, `.next/`, `.wrangler/`, or generated `next-env.d.ts`.
- Never hand-edit lockfiles to accomplish a styling change.
- Never modify signing files, keystores, `.env*` secrets, tokens, API keys, or deployment credentials.
- Never overwrite unrelated dirty/untracked files.
- Never replace `admin-dashboard/public/og-learnmate-admin.png` or platform icons unless the requested work explicitly includes branded assets and corresponding metadata/platform validation.

## Checklist before completion

- [ ] The affected surface and central theme source were inspected.
- [ ] Existing Material roles or CSS tokens were reused where appropriate.
- [ ] New literals are centralized and semantically named when reuse is expected.
- [ ] Selected, disabled, focus, hover, success, warning, error, and destructive states remain coherent.
- [ ] Contrast, non-color cues, Vietnamese text length, responsive layout, and reduced motion were considered.
- [ ] No nonexistent shared-token, dark-mode, font, or generator architecture was assumed.
- [ ] Relevant mobile/admin verification commands pass.
- [ ] Assets, dependencies, generated files, secrets, and unrelated work were not changed accidentally.
