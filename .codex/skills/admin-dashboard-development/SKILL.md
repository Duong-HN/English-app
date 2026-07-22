---
name: admin-dashboard-development
description: "Develop, debug, review, refactor, test, or configure the LearnMate administrator web application under admin-dashboard/. Use for Vinext/Next App Router and React changes, dashboard view flow, typed AdminApi integration, JWT session behavior, API Console work, Cloudflare Worker/Sites configuration, admin tests, or dashboard build and Docker tasks."
---

# Admin Dashboard Development

## Purpose

Maintain the existing LearnMate Admin architecture: a Vietnamese-first React client rendered with Next App Router conventions, built by Vinext/Vite, and served through a Cloudflare Worker while calling the FastAPI backend directly.

## When to use

- Change files under `admin-dashboard/app/`, `admin-dashboard/worker/`, or dashboard configuration.
- Add or modify an administrator view, filter, mutation, API preset, session flow, metadata, test, build, or deployment behavior.
- Diagnose dashboard rendering, CORS, backend URL, Worker, or Vinext issues.
- Review a dashboard change for architectural, security, accessibility, or test regressions.

## Project-specific rules

- Preserve the current runtime: scripts in `admin-dashboard/package.json` use `vinext dev`, `vinext build`, and `vinext start`, not the conventional Next CLI.
- Keep `app/layout.tsx` and `app/page.tsx` as server components unless browser behavior truly requires a client boundary. `app/admin-app.tsx` and `app/api-console.tsx` are the client surfaces.
- Treat `/` as the only current App Router route. Dashboard sections use the `View` union, `navItems`, and conditional rendering in `AdminApp`; do not claim that tabs are URL routes.
- Put backend contracts and ordinary HTTP calls in `app/lib/api.ts`. Preserve snake_case fields from `backend/app/schemas.py`; do not scatter raw `fetch` calls through UI components.
- Keep ordinary non-2xx calls throwing `ApiError`. Keep `AdminApi.consoleRequest()` inspectable for non-2xx responses and preserve its single-slash path and same-origin checks.
- Keep JWT and selected backend URL in `sessionStorage`. Never move the JWT to `localStorage`, logs, URLs, Console history, or generated cURL.
- Keep client role checks as UX only. Real authorization remains `require_admin` in `backend/app/dependencies.py`.
- Use backend filtering and `limit`/`offset`; the current UI uses `PAGE_SIZE = 20`.
- Keep feature state local with React hooks. There is no global store, repository layer, DI container, server action layer, or query-cache library.
- Do not add mock dashboard data. `admin-dashboard/README.md` and the overview explicitly promise real backend data.
- Do not infer a dashboard database from `worker/index.ts` declaring `DB`. `.openai/hosting.json` has `d1` and `r2` set to `null`; `db/` and `drizzle/` are empty.
- Preserve Sites/Vinext wiring in `vite.config.ts`: Worker entry, `nodejs_compat`, RSC/SSR Cloudflare environment, project-local Wrangler state, and `sites()` packaging.
- Preserve the `.openai/hosting.json` `project_id`. Change logical D1/R2 bindings only for an explicitly requested site-owned persistence feature.
- Follow strict TypeScript, ESLint core-web-vitals/TypeScript rules, two-space indentation, double quotes, and semicolons.
- Preserve existing dirty or untracked work. Start by inspecting `git status --short`.

## Best practices

- Construct `AdminApi` with `useMemo` so data effects do not rerun on every render.
- Follow the existing `active` cleanup pattern for async effects and clear intervals in effect cleanup.
- Represent loading, empty, error, success, and busy mutation states explicitly.
- Separate draft search text from applied filters and reset pagination when filters change.
- Confirm destructive actions, close selected dialogs after successful deletion, and surface `readableError()` messages.
- Keep API Console history metadata-only and capped; continue substituting `$ADMIN_TOKEN` in `buildCurl()`.
- Keep browser-facing backend URLs public and align the dashboard origin with backend `ALLOWED_ORIGINS`.
- Add an actual App Router segment only when a feature must be bookmarkable, deep-linkable, or independently rendered.
- Apply `ui-development`, `theme-system`, and `localization` guidance for visual or copy changes.
- Update focused tests and documentation in the same change as behavior or environment requirements.

## Common mistakes

- Running `next dev` or treating the production artifact as a conventional Next Node server.
- Accessing `window`, `navigator`, or `sessionStorage` during server rendering.
- Recreating `AdminApi` during each render and causing effect loops.
- Trusting `response.user.role` instead of backend authorization.
- Bypassing the API client, omitting bearer authorization, or changing API field casing.
- Removing the API Console origin guard or copying a live JWT into cURL/history.
- Adding Redux, Zustand, Axios, React Query, Tailwind, Drizzle, Firebase, or a repository abstraction without a concrete architectural requirement.
- Assuming empty `db/`, `drizzle/`, or `examples/d1/` directories implement persistence.
- Editing generated `dist/`, `.vinext/`, `.wrangler/`, or dependency files by hand.
- Changing login or metadata copy without updating SSR string assertions.

## Required workflow

1. Run `git status --short` and identify current user changes before editing.
2. Read the touched component plus `app/lib/api.ts`; read the matching backend route/schema for contract changes.
3. Decide whether the work belongs in a server component, client component, API helper, Worker, or backend.
4. Implement the smallest compatible change using existing hooks, state patterns, API errors, CSS classes, and Vietnamese copy.
5. Add or update a focused `node:test` case. Keep SSR behavior checks in `tests/rendered-html.test.mjs` and pure/API helper checks in `tests/api-console.test.mjs`.
6. Update `admin-dashboard/README.md` or root deployment/API docs when behavior, endpoints, or environment variables change.
7. From `admin-dashboard/`, run `npm run lint` and `npm test`. `npm test` performs the production Vinext build before both test files.
8. For runtime/container changes, also build the dashboard Docker image. For dependency changes, update `package-lock.json` through npm and run the production dependency audit.
9. Recheck `git diff --check` and confirm no generated, secret, or unrelated files changed.

## Examples from this repository

- Server-to-client composition: `app/page.tsx` reads `NEXT_PUBLIC_API_BASE_URL` and renders `AdminApp`; `app/layout.tsx` supplies Vietnamese metadata.
- Session restoration and admin gating: `AdminApp`, `LoginScreen`, `TOKEN_KEY`, and `API_KEY` in `app/admin-app.tsx`.
- Local view navigation and stable API injection: `Dashboard`, `View`, `navItems`, and the memoized `AdminApi` in `app/admin-app.tsx`.
- Paginated mutation flow: `UsersPage`; learning-path list/delete flow: `LearningPathsPage` and `AdminApi.learningPaths()`.
- Safe request workbench: `ApiConsole` in `app/api-console.tsx`, `AdminApi.consoleRequest()` in `app/lib/api.ts`, and `buildCurl()` in `app/lib/api-console.ts`.
- Worker delegation and image optimization: `worker/index.ts`.
- Build metadata packaging: `sites()` in `build/sites-vite-plugin.ts` and its use in `vite.config.ts`.
- SSR and source contract tests: `tests/rendered-html.test.mjs`; header/cURL/API tests: `tests/api-console.test.mjs`.

## Files to reference

- `admin-dashboard/app/page.tsx`
- `admin-dashboard/app/layout.tsx`
- `admin-dashboard/app/admin-app.tsx`
- `admin-dashboard/app/api-console.tsx`
- `admin-dashboard/app/lib/api.ts`
- `admin-dashboard/app/lib/api-console.ts`
- `admin-dashboard/app/globals.css`
- `admin-dashboard/package.json`
- `admin-dashboard/tsconfig.json`
- `admin-dashboard/eslint.config.mjs`
- `admin-dashboard/vite.config.ts`
- `admin-dashboard/worker/index.ts`
- `admin-dashboard/.openai/hosting.json`
- `admin-dashboard/tests/`
- `backend/app/schemas.py`
- `backend/app/dependencies.py`
- `backend/app/routers/admin.py`
- `.github/workflows/ci.yml`
- `docs/DEPLOYMENT.md`

## Files that should never be modified

- Never hand-edit `admin-dashboard/node_modules/`, `dist/`, `.vinext/`, `.next/`, `.wrangler/`, `coverage/`, `outputs/`, or `work/`.
- Never hand-edit generated `next-env.d.ts` or individual entries in `package-lock.json`.
- Never commit real `.env*` values, JWTs, passwords, API keys, Console credentials, or deployment hook URLs.
- Never overwrite unrelated dirty/untracked project files.
- Never change `.openai/hosting.json` `project_id` as part of an ordinary application feature.

## Checklist before completion

- [ ] Existing worktree changes were identified and preserved.
- [ ] The change respects the server/client boundary and Vinext runtime.
- [ ] API types, paths, authorization, pagination, and errors match the backend.
- [ ] JWT and Console history/cURL safety remain intact.
- [ ] Loading, empty, error, busy, and destructive-action states are handled.
- [ ] Vietnamese copy, accessibility, and responsive behavior are preserved.
- [ ] No inactive D1/R2 or uninstalled architecture was assumed.
- [ ] Focused tests and relevant documentation were updated.
- [ ] `npm run lint` and `npm test` pass.
- [ ] Generated, secret, and unrelated files are absent from the diff.
