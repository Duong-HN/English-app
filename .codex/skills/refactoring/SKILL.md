---
name: refactoring
description: "Restructure LearnMate backend, Flutter, or administrator code while preserving observable behavior and contracts. Use for splitting large files, extracting components/services/helpers, removing duplication, renaming, or simplifying code without changing product behavior."
---

# Refactoring

## Purpose

Improve maintainability through small, behavior-preserving transformations grounded in characterization tests.

## When to use

Use for structural cleanup, file extraction, duplication removal, naming changes, dependency seam cleanup, or preparation for a clearly scoped feature.

## Project-specific rules

- Preserve the current pragmatic architecture. A refactor alone does not justify adding repositories, use cases, Firebase, Redux/Riverpod, a DI container, or a router package.
- Keep FastAPI route paths, response models, status codes, owner filters, RBAC, transactions, and audit behavior unchanged unless the request includes a contract change.
- Preserve Flutter constructor injection, service interfaces, stable widget keys, four-tab indices, `IndexedStack` retention, async `mounted` checks, and disposal.
- Preserve admin session restoration, `View` semantics, memoized `AdminApi`, effect cleanup, API Console origin/token protections, SSR login output, and global CSS conventions.
- Separate behavior changes from structural moves so review and rollback remain clear.
- Inspect dirty/untracked work first and do not use resets or broad rewrites over it.

## Best practices

- Add or strengthen characterization tests before moving high-risk code.
- Extract by responsibility with narrow interfaces and keep data conversion at existing boundaries.
- Move code in small compilable/testable steps and run focused checks after each group.
- Preserve import direction and avoid circular dependencies.
- Use existing names and patterns unless the rename materially clarifies responsibility.
- Update docs only when the documented structure or workflow truly changes.

## Common mistakes

- Calling a feature change a refactor and omitting new behavior tests.
- Splitting files while also replacing state management, routing, persistence, or styling.
- Moving direct ORM code behind an invented repository abstraction with no project need.
- Losing FastAPI router registration or route ordering during extraction.
- Recreating Flutter services inside widgets and breaking test injection.
- Changing tab indices, keys, state retention, or controller cleanup while moving widgets.
- Accessing `sessionStorage` during SSR after extracting admin session logic.
- Editing generated registrants, build output, or lockfile content manually.

## Required workflow

1. Define the exact behavior that must remain unchanged and list its current tests.
2. Run focused baseline tests and inspect `git status --short`.
3. Add characterization coverage for unprotected behavior.
4. Choose one extraction/rename/simplification boundary at a time.
5. Apply a small patch, format/lint, and run focused tests.
6. Repeat until the target structure is reached without mixing feature changes.
7. Run the full affected component gate and inspect the diff for accidental contract/copy/style changes.
8. Update architecture/component docs only if file ownership or developer workflow changed.

## Examples from this repository

- `mobile/lib/src/features/home/home_page.dart` is a large factual extraction candidate; its study, learning path, history, and profile widgets can be split only while preserving keys, tab indices, services, and widget tests.
- `admin-dashboard/app/admin-app.tsx` contains shell and feature views; extraction must preserve local state/effect behavior and `tests/rendered-html.test.mjs` expectations.
- `backend/app/routers/admin.py` has reusable response/audit/lockout helpers; extraction must keep authorization and mutations in the same transaction.
- `admin-dashboard/app/lib/api-console.ts` demonstrates extracting pure helpers that can be tested with `node:test`.

## Files to reference

- The target source file and every direct caller/importer
- Adjacent tests in `backend/tests/`, `mobile/test/`, or `admin-dashboard/tests/`
- `docs/ARCHITECTURE.md`
- `backend/pyproject.toml`
- `mobile/analysis_options.yaml`
- `admin-dashboard/eslint.config.mjs`

## Files that should never be modified

- Never modify generated/vendor/state trees, local databases, secrets, keystores, or caches.
- Never hand-edit lockfile internals or Flutter generated plugin registrants.
- Never rewrite applied migrations during a code-only refactor.
- Never overwrite unrelated tracked or untracked user changes.

## Checklist before completion

- [ ] Observable behavior and public contracts are unchanged.
- [ ] Characterization tests cover the moved high-risk behavior.
- [ ] Existing DI/state/routing/persistence conventions remain intact.
- [ ] The diff contains structural changes only, or behavior changes are explicitly separated and tested.
- [ ] Full affected format/lint/test gates pass.
- [ ] Generated, secret, and unrelated files are untouched.
