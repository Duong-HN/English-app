---
name: routing
description: >-
  Add, change, debug, review, or test navigation and route contracts across LearnMate. Use for Flutter authentication gating, NavigationBar tabs, IndexedStack state retention, dialog Navigator calls, or future screen/deep-link work; for the Next-compatible admin app's file route and local Dashboard View navigation; and for FastAPI APIRouter definitions, prefixes, methods, path parameters, authorization dependencies, response models, and client endpoint synchronization. Do not assume go_router, auto_route, React Router, or URL-backed admin panels exist.
---

# Routing

## Purpose

Keep learner navigation, administrator panel selection, and HTTP route contracts coherent across UI, clients, backend, tests, documentation, and security boundaries.

## When to use

- Add, remove, reorder, or rename a Flutter screen/tab or admin dashboard panel.
- Add URL/deep-link behavior, dialogs, redirects, authentication gates, or navigation restoration.
- Add or change a FastAPI endpoint, prefix, HTTP method, path/query parameter, response model, or authorization dependency.
- Diagnose 404/405 errors, stale client paths, wrong panel rendering, lost tab state, or unauthorized route exposure.

## Project-specific rules

- Flutter has no routing package or named route table. `LearnMateApp` selects splash, `AuthPage`, or `HomePage` through an `AnimatedBuilder` in `MaterialApp.home`.
- `HomePage` navigation is index-based and state-preserving: Study=0, Learning Path=1, History=2, Profile=3 in one `IndexedStack` and `NavigationBar`.
- Keep `_selectPage` synchronized with destination order. Index 1 refreshes `_LearningPathPage`; index 2 refreshes `_HistoryPage` through `GlobalKey` state methods.
- Flutter `Navigator` is currently used only to return a boolean from the delete confirmation dialog. Do not claim deep links, named routes, or back-stack screen navigation exist.
- The admin application has one Next-compatible file route, `admin-dashboard/app/page.tsx`. `Dashboard` switches six panels with local `View` state, `navItems`, and conditional rendering; panel changes do not update the URL and are not deep-linkable.
- Keep the admin `View` union, desktop/mobile nav lists, heading lookup, conditional content, `data-testid` values, and navigation callbacks synchronized.
- FastAPI routers define local prefixes: `/auth`, `/analyses`, `/learning-paths`, `/admin`; `backend/app/main.py` mounts them under `/api/v1`. Health routes remain unversioned under `/health`.
- Preserve route-level request/response models and dependencies. Learner routes use `get_current_user`; administrator routes use `require_admin`; the UI cannot grant access by hiding a panel.
- Coordinate endpoint changes with `mobile/lib/src/core/api_client.dart`, `admin-dashboard/app/lib/api.ts`, API Console presets, Postman collections, tests, and docs.
- Treat existing external paths as contracts. Prefer additive versioned changes over silently repurposing a method/path.

## Best practices

- Choose the routing surface deliberately: local transient panel/tab, Flutter screen/back stack, URL route, or HTTP endpoint.
- Keep static backend paths such as `/current` and `/generate` explicit and declared so they cannot be confused with identifier paths.
- Use correct HTTP semantics and status codes; retain Pydantic `response_model` validation on API routes.
- Put authentication/authorization in backend dependencies and application gates, not only button visibility.
- Preserve Flutter `IndexedStack` when state retention is required; add a router only when URL/deep-link/back-stack requirements justify a migration.
- Add stable keys/test IDs for new interactive destinations and test the route from the user's entry point.
- Update route documentation and client contract tests in the same change.

## Common mistakes

- Installing `go_router`, `auto_route`, or React Router for one local tab/panel without a migration requirement.
- Reordering Flutter destinations but leaving refresh indices and `GlobalKey` targets unchanged.
- Adding an admin `View` value to only one of the union, `navItems`, mobile nav, title, and render branches.
- Expecting browser back/forward or a copied URL to restore the current admin `View`; current navigation is local state.
- Mounting a backend router with a duplicate `/api/v1` prefix or changing a route without updating both clients and Postman/tests.
- Omitting `get_current_user`/`require_admin`, relying on client-side gating, or weakening user-owned query filters.
- Returning unvalidated dictionaries when an established response model exists.
- Editing generated Next/Flutter routing output or overwriting unrelated dirty work.

## Required workflow

1. Inspect `git status --short` and trace the route from entry point through UI navigation/client method to backend router, tests, and documentation.
2. Classify it as Flutter auth/tab/dialog navigation, admin local panel navigation, a real URL route, or a FastAPI HTTP contract.
3. Record current names, indices, prefixes, methods, schemas, auth dependencies, and state-retention expectations.
4. Make the smallest synchronized change at every source of truth; do not introduce a router package for local state alone.
5. Update client URLs, API Console presets, Postman examples, docs, stable keys/test IDs, and authorization checks as applicable.
6. Add focused navigation/contract tests for success, unauthorized access, not found, and retained/restored state where relevant.
7. Run Flutter checks, admin lint/tests, and/or backend Ruff/pytest for every affected surface.
8. Inspect the final diff for stale paths, index mismatches, generated files, secrets, and unrelated changes.

## Examples from this repository

- `mobile/lib/src/app.dart` gates the root with `initialized` and `isAuthenticated` rather than pushing routes.
- `HomePage` in `mobile/lib/src/features/home/home_page.dart` holds four pages in an `IndexedStack`; `_selectPage` refreshes path/history tabs.
- The history delete dialog uses `showDialog<bool>` and `Navigator.pop(context, true/false)` without defining a screen route.
- `admin-dashboard/app/page.tsx` is the one file route; `Dashboard` in `admin-app.tsx` maps the `View` union to six local panels.
- `backend/app/main.py` mounts router modules; `backend/app/routers/learning_paths.py` exposes `/api/v1/learning-paths/generate`, `/current`, collection GET, and ID DELETE.
- `mobile/test/home_page_test.dart` navigates by visible tab labels and stable learning-path keys; backend tests exercise exact HTTP paths and authorization.

## Files to reference

- `mobile/lib/src/app.dart`
- `mobile/lib/src/features/home/home_page.dart`
- `mobile/test/widget_test.dart`, `mobile/test/home_page_test.dart`
- `mobile/lib/src/core/api_client.dart`, `mobile/test/api_client_test.dart`
- `admin-dashboard/app/page.tsx`, `admin-dashboard/app/layout.tsx`
- `admin-dashboard/app/admin-app.tsx`, `admin-dashboard/app/lib/api.ts`
- `admin-dashboard/app/lib/api-console.ts`, `admin-dashboard/tests/*.mjs`
- `backend/app/main.py`, `backend/app/routers/*.py`
- `backend/app/dependencies.py`, `backend/app/schemas.py`, `backend/tests/*.py`
- `postman/`, `.postman/`, `docs/ARCHITECTURE.md`, `docs/TEST_PLAN.md`

## Files that should never be modified

- Never edit generated Flutter registrants/ephemeral files, `mobile/.dart_tool/`, `mobile/build/`, admin `.next/`/`.vinext/`/`node_modules/`, or Python/test caches.
- Never hand-edit dependency lockfiles or Flutter-generated metadata to make a route compile.
- Never edit or commit backend `.env`, databases, Android signing files, local SDK paths, API keys, JWTs, or deployment secrets.
- Never discard unrelated tracked or untracked work while changing routes.

## Checklist before completion

- [ ] The navigation/route surface is correctly classified and uses the existing mechanism.
- [ ] Flutter tab indices, refresh keys, state retention, and auth gating remain coherent.
- [ ] Admin `View`, nav items, headings, render branches, test IDs, and URL expectations agree.
- [ ] Backend prefix, method, parameters, response model, auth dependency, and user isolation are correct.
- [ ] Mobile/admin clients, Postman examples, docs, and tests use the same path contract.
- [ ] Relevant stack checks pass, including unauthorized/not-found coverage when applicable.
- [ ] No generated, secret, unrelated, or user-owned dirty file changed.
