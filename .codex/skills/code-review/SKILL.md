---
name: code-review
description: "Review LearnMate diffs for correctness, security, privacy, architecture fit, contract alignment, tests, performance, delivery, and documentation. Use for pull-request review, pre-merge audits, regression analysis, or requests to assess code without implementing changes."
---

# Code Review

## Purpose

Produce an evidence-backed, severity-ordered review against this repository's actual behavior and release gates.

## When to use

Use when reviewing a diff, branch, pull request, feature slice, migration, dependency update, or release candidate.

## Project-specific rules

- Lead with actionable findings, not a summary. Include the file and line, impact, triggering scenario, and smallest sound correction.
- Distinguish introduced defects from pre-existing dirty work. Inspect `git status --short`, the requested diff, and untracked authored files.
- Judge changes against the pragmatic current architecture; do not demand Clean Architecture, Repository Pattern, Firebase, or a new state/DI framework.
- Trace API changes through Pydantic, routers, ORM/provider, Flutter `ApiClient`, dashboard `AdminApi`, UI, tests, Postman, and docs.
- Prioritize identity, owner scoping, admin RBAC/audit, secrets, learner data, prompt injection, and transcript-versus-pronunciation boundaries.
- Treat migrations, platform permissions, Vinext/Worker build files, workflows, and release signing as high-risk surfaces.
- If no findings exist, state that plainly and name residual test/coverage gaps.
- A review request is read-only unless the user separately authorizes fixes.

## Best practices

- Reproduce suspected failures with focused read-only commands or tests when feasible.
- Check both the changed lines and the assumptions of their callers/consumers.
- Verify async cleanup: Flutter `mounted`, React effect activity/timer cleanup, HTTP client/resource closure.
- Verify bounded queries, pagination, indexes, timeouts, and no full-history/provider payload leaks.
- Review generated lockfile changes through their source manifest and package-manager outcome, not line by line alone.
- Keep style-only suggestions separate from correctness findings.

## Common mistakes

- Reporting speculative issues without a concrete execution path.
- Missing untracked migrations/tests or reviewing only `git diff`.
- Trusting client-side admin checks or omitting learner ownership filters.
- Overlooking that admin `npm test` builds Vinext output before tests.
- Treating empty D1/Drizzle folders or Firebase mentions in `ideal.md` as current architecture.
- Recommending direct edits to generated plugin registrants, build output, caches, or lockfile internals.
- Ignoring product-safety wording because it appears to be copy-only.

## Required workflow

1. Confirm review scope; run `git status --short`, `git diff --stat`, and the relevant diff including untracked authored files.
2. Read repository rules, nearby implementation, tests, and canonical docs.
3. Classify changes by backend, mobile, admin, data, auth/security, AI, delivery, and docs.
4. Trace each changed contract end to end and test plausible failure paths.
5. Run focused validation when it can confirm or refute a finding.
6. Rank findings by user/security/data/release impact; avoid duplicates.
7. Report file/line evidence, impact, and a concrete fix direction.
8. State remaining test gaps and checks not run.

## Examples from this repository

- Review a learner-owned endpoint against the filters in `backend/app/routers/analyses.py` and `backend/app/routers/learning_paths.py`.
- Review an admin mutation against `_ensure_another_active_admin()` and `_record_audit()` in `backend/app/routers/admin.py`.
- Review Gemini changes against Pydantic validation and `responseJsonSchema` assertions in `backend/tests/test_ai.py`.
- Review API Console changes against same-origin enforcement in `admin-dashboard/app/lib/api.ts` and token-redacted cURL in `app/lib/api-console.ts`.
- Review mobile speech copy against `mobile/lib/src/core/speech_service.dart` and the architecture prohibition on pronunciation claims.

## Files to reference

- `docs/ARCHITECTURE.md`
- `docs/API.md`
- `docs/TEST_PLAN.md`
- `SECURITY.md`
- `.github/workflows/ci.yml`
- `scripts/check.ps1`
- Component implementation and adjacent tests for every changed file

## Files that should never be modified

- Do not modify any file during a review-only task.
- Never alter or reveal `.env`, keystores, tokens, local Postman values, local databases, or provider credentials.
- Never edit generated/vendor/state directories or overwrite unrelated dirty work.

## Checklist before completion

- [ ] The full requested diff, including relevant untracked files, was inspected.
- [ ] Findings are reproducible, severity-ordered, and tied to file/line evidence.
- [ ] API, database, auth, AI/privacy, UI, test, and delivery impact were considered.
- [ ] Findings do not impose architectures absent from the repository.
- [ ] Checks run and residual risks are stated.
- [ ] No files were changed during a review-only request.
