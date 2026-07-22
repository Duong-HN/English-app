---
name: state-management
description: >-
  Design, change, debug, review, or test state ownership and asynchronous state transitions across LearnMate. Use for Flutter AuthController/ChangeNotifier, AnimatedBuilder, StatefulWidget setState, FutureBuilder, tab refresh and lifecycle work; React useState/useEffect/useMemo/useCallback, session restoration, local Dashboard View navigation, filters, dialogs, API Console history, or sessionStorage; and FastAPI request-scoped versus persisted state. Preserve the repository's native framework patterns—there is no Provider, Riverpod, BLoC, Redux, Zustand, or server-side state container.
---

# State Management

## Purpose

Keep state at the narrowest correct owner across Flutter, the React administrator console, and the stateless FastAPI service while preserving lifecycle, persistence, and test behavior.

## When to use

- Add or move loading, error, form, selection, filter, pagination, session, tab, dialog, or cached data state.
- Change asynchronous effects, refresh behavior, restoration, logout, persistence, or component/widget lifecycles.
- Diagnose stale UI, duplicate requests, updates after disposal/unmount, lost tab state, or cross-user data leakage.
- Review a proposal to introduce a state-management package or global mutable state.

## Project-specific rules

- Flutter application/session state belongs to `AuthController extends ChangeNotifier`; `LearnMateApp` observes it with `AnimatedBuilder` and selects splash/auth/home from `initialized` and `isAuthenticated`. The controller also owns `loading`, `error`, `user`, and the client token for authentication flows and session state.
- Keep feature state local to its `State` object when no other widget owns it. Existing examples include study mode/result/capture flags, learning-path form/result flags, and history's stored `Future`.
- Preserve `HomePage`'s `IndexedStack`: all four tab states survive selection changes. Learning-path/history refresh uses `GlobalKey` state methods on tab selection.
- After Flutter awaits or plugin callbacks, check `mounted` before `setState`; dispose text controllers and stop owned services.
- In the admin console, keep browser UI state in React hooks inside the owning client component. `AdminApp` owns session restoration; `Dashboard` owns the local `View`; each page owns its filters, page, data, selection, busy, and error state.
- Keep `AdminApi` memoized from `session.baseUrl` and `session.token`; effects must list real dependencies and clean up timers or ignore late results with an `active` guard.
- Persist only the existing browser-scoped data in `sessionStorage`: admin JWT/base URL and the bounded API Console history. Do not move the JWT to `localStorage` or global browser state.
- Treat backend request handlers as stateless. Durable state belongs in SQLAlchemy models; request state arrives through FastAPI `Depends`; `get_settings` is the intentional `lru_cache` configuration singleton.
- Do not introduce Provider/Riverpod/BLoC/GetX, Redux/Zustand/Context, or a server state store without an explicit, evidence-backed migration.
- Preserve user isolation: mobile/auth state and backend queries must never expose another user's analyses or learning paths.

## Best practices

- Decide state lifetime first: one callback, widget/component, app session, browser tab, request, or database.
- Store source state, derive display values during build/render or with `useMemo` only when identity/cost matters; avoid mirrored state that can diverge.
- Model async work with explicit loading/error/data transitions and clear stale results when the request semantics change.
- Use `finally` for busy flags and cancellation/active guards for late callbacks. Do not call Flutter `setState` after disposal or React setters from an obsolete effect.
- Reset pagination when applied filters change; keep draft query separate from applied query, as the admin pages do.
- Bound persisted browser history and parse storage defensively, following `readHistory` in `admin-dashboard/app/api-console.tsx`.
- Keep backend authorization and transaction state request-scoped through `get_current_user` and `get_db`; commit/rollback deliberately.
- Add focused transition tests: initial, loading, success, empty, error, refresh, restoration, and logout where relevant.

## Common mistakes

- Moving local state into a new global framework without multiple proven owners.
- Recreating `AdminApi` each render or adding incomplete effect dependency arrays, causing request loops or stale credentials.
- Persisting filters, responses, passwords, full learner submissions, or JWTs beyond the existing tab-scoped policy.
- Replacing Flutter `IndexedStack` with conditional children and unintentionally losing study/form state.
- Changing tab order without changing refresh indices/keys; changing the admin `View` union without `navItems` and conditional rendering.
- Updating UI after an await without `mounted`/active checks or leaving health-check timers running.
- Keeping mutable per-user state in FastAPI module globals or reusing a SQLAlchemy `Session` across requests.
- Confusing React local `View` state with URL routing or secure server authorization.

## Required workflow

1. Inspect `git status --short` and trace every reader, writer, persistence boundary, and cleanup path for the state being changed.
2. Classify its lifetime and select the existing owner: Flutter controller/widget, React component/sessionStorage, FastAPI request dependency, or database model.
3. Write down transitions and invalidation triggers, including initial/loading/success/empty/error/refresh/logout.
4. Implement using the existing framework primitive; avoid adding a dependency unless current primitives cannot meet demonstrated shared-state needs.
5. Add lifecycle protection: `mounted`, effect cleanup/active flag, timer cleanup, bounded storage, or request-scoped DB session.
6. Update navigation refresh, filters/pagination, persistence, and authorization behavior that depends on the state.
7. Add focused Flutter, Node, or pytest coverage for transitions and regression risks.
8. Run the affected stack's format/lint/analyze/tests, then inspect the diff for unrelated or generated changes.

## Examples from this repository

- `AuthController` in `mobile/lib/src/core/auth_controller.dart` restores a secure token, loads the profile, notifies listeners around authentication, and clears state on logout.
- `_StudyPageState`, `_LearningPathPageState`, and `_HistoryPageState` in `mobile/lib/src/features/home/home_page.dart` own local asynchronous feature state.
- `AdminApp` in `admin-dashboard/app/admin-app.tsx` restores and validates a tab-scoped session; `Dashboard` uses the `View` union for six local panels and memoizes `AdminApi`.
- Admin list pages keep `query` separate from `appliedQuery`, reset/reload pages explicitly, and use effects with active guards.
- `ApiConsole` in `admin-dashboard/app/api-console.tsx` bounds defensive session history to 12 entries.
- `get_db` in `backend/app/db.py` yields and closes a request session; user-owned records in `backend/app/routers/analyses.py` and `learning_paths.py` are database state, not process memory.

## Files to reference

- `mobile/lib/src/app.dart`
- `mobile/lib/src/core/auth_controller.dart`, `mobile/lib/src/core/token_store.dart`
- `mobile/lib/src/features/auth/auth_page.dart`
- `mobile/lib/src/features/home/home_page.dart`
- `mobile/test/auth_controller_test.dart`, `mobile/test/widget_test.dart`, `mobile/test/home_page_test.dart`
- `admin-dashboard/app/admin-app.tsx`
- `admin-dashboard/app/api-console.tsx`
- `admin-dashboard/app/lib/api.ts`
- `admin-dashboard/tests/*.mjs`
- `backend/app/config.py`, `backend/app/db.py`, `backend/app/dependencies.py`
- `backend/app/models.py`, `backend/app/routers/*.py`, `backend/tests/*.py`
- `docs/ARCHITECTURE.md`, `SECURITY.md`

## Files that should never be modified

- Never edit generated/artifact directories: `mobile/.dart_tool/`, `mobile/build/`, Flutter platform `ephemeral/` and registrants, `admin-dashboard/node_modules/`, `.next/`, `.vinext/`, coverage output, Python caches, or `.pytest_cache/`.
- Never hand-edit `mobile/pubspec.lock`, `admin-dashboard/package-lock.json`, or generated Flutter metadata/registrants; use the owning package tool.
- Never edit or commit browser/server/mobile secrets, backend `.env`, databases, Android signing files, or local SDK configuration.
- Never discard unrelated tracked or untracked work while reorganizing state.

## Checklist before completion

- [ ] State has one clear owner and the narrowest correct lifetime.
- [ ] Loading, success, empty, error, refresh, and logout/invalidation transitions are coherent.
- [ ] Flutter mounted/disposal and React effect/timer cleanup are safe.
- [ ] Persistence remains minimal, tab-scoped where designed, and free of passwords/full learner data.
- [ ] Backend state is request-scoped or database-persisted with user isolation.
- [ ] No uninstalled state framework or unnecessary global mutable state was added.
- [ ] Relevant Flutter, admin, and/or backend tests and quality checks pass.
- [ ] No generated, secret, unrelated, or user-owned dirty file changed.
