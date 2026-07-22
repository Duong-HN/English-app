---
name: performance-optimization
description: "Diagnose and improve LearnMate latency, rendering, database, AI, networking, build, or resource usage using measured evidence. Use for slow endpoints, expensive provider calls, janky Flutter/admin UI, excessive queries, large payloads, polling, or build/runtime performance work."
---

# Performance Optimization

## Purpose

Improve a measured bottleneck while preserving correctness, privacy, testability, and the existing architecture.

## When to use

Use when a user reports slowness, metrics identify a hotspot, a feature adds material data/AI/device work, or a release/build becomes resource-heavy.

## Project-specific rules

- Establish a baseline before changing code; this repository has no dedicated benchmark suite or production observability yet.
- Backend queries use synchronous SQLAlchemy sessions. Preserve bounded `limit`/`offset`, owner/admin filters, indexed ownership/type/time fields, and `pool_pre_ping`.
- Learning-path personalization intentionally loads at most 20 recent analyses and sends aggregate counts/scores/issue titles, not full submissions.
- Gemini calls use a configured timeout and structured output. Do not add retries that duplicate billable requests without idempotency and an explicit requirement.
- Flutter uses a state-preserving `IndexedStack`, eager page construction, a 30-second API timeout, and bounded OCR images (`imageQuality: 90`, `maxWidth: 2048`). Measure before replacing these tradeoffs.
- Admin uses backend pagination with page size 20, 30-second health polling with cleanup, memoized `AdminApi`, and concurrent overview fetches.
- Do not cache JWTs, passwords, learner submissions, or admin responses in a broader persistence layer to gain speed.
- Keep OCR on-device and avoid uploading raw images/audio; current persistence stores text/results only.

## Best practices

- Measure wall time, query count/shape, payload size, rebuild frequency, memory, and provider latency at the relevant boundary.
- Optimize the dominant component first and record before/after conditions.
- Prefer query/index/pagination fixes, smaller validated payloads, localized widget/component rebuilds, and correct lifecycle cleanup.
- Keep cancellation/unmount handling and readable loading/error states.
- Add a regression test or lightweight measurement harness when an invariant can be automated.
- Treat dependency, caching, concurrency, and retry additions as architectural changes requiring security and failure-mode review.

## Common mistakes

- Performing a broad state-management or ORM rewrite without measurements.
- Removing `IndexedStack` without accounting for tab state retention, or keeping expensive eager work without measuring it.
- Loading all analyses/users/paths in a client to avoid pagination requests.
- Sending full learner history to Gemini for personalization.
- Parallelizing database work through a shared SQLAlchemy `Session`.
- Polling faster without visibility/focus logic or timer cleanup.
- Hiding latency behind stale or sensitive caches.
- Benchmarking debug Flutter or development Vinext output as release performance.

## Required workflow

1. Define the slow scenario, target platform/environment, dataset, and success metric.
2. Capture a repeatable baseline and locate time/resource distribution.
3. Read the relevant lifecycle, query, timeout, pagination, and privacy constraints.
4. Apply the smallest optimization that addresses the measured bottleneck.
5. Add regression coverage for behavior and any measurable invariant.
6. Repeat the same measurement and compare results.
7. Run the affected component's full quality gate and release-mode build if rendering/build performance changed.
8. Document the measurement, tradeoffs, and remaining limits.

## Examples from this repository

- `backend/app/routers/learning_paths.py` bounds recent activity to 20 rows and aggregates it before provider use.
- `backend/app/routers/admin.py` paginates list APIs and uses grouped/count queries instead of loading related objects one by one.
- `mobile/lib/src/features/home/home_page.dart` preserves tab state with `IndexedStack` and refreshes path/history only on selected tabs.
- `mobile/lib/src/core/ocr_service.dart` bounds camera/gallery input before ML Kit processing.
- `admin-dashboard/app/admin-app.tsx` memoizes `AdminApi`, fetches overview data concurrently, and cleans a 30-second health timer.

## Files to reference

- `backend/app/db.py`
- `backend/app/models.py`
- `backend/app/routers/admin.py`
- `backend/app/routers/learning_paths.py`
- `backend/app/ai.py`
- `mobile/lib/src/core/api_client.dart`
- `mobile/lib/src/core/ocr_service.dart`
- `mobile/lib/src/features/home/home_page.dart`
- `admin-dashboard/app/admin-app.tsx`
- `admin-dashboard/app/lib/api.ts`

## Files that should never be modified

- Never edit generated build profiles/artifacts, caches, local databases, `dist/`, `build/`, `.dart_tool/`, `.vinext/`, `.wrangler/`, or vendor trees.
- Never weaken validation, ownership, RBAC, audit, privacy, or AI safety to improve a metric.
- Never add real learner data or credentials to benchmarks.
- Never overwrite unrelated in-progress work.

## Checklist before completion

- [ ] A repeatable baseline and target metric were recorded.
- [ ] The dominant bottleneck was identified rather than guessed.
- [ ] Correctness, state retention, privacy, and failure behavior remain intact.
- [ ] Before/after measurements use comparable conditions.
- [ ] Regression tests and the affected release-quality gate pass.
- [ ] New caching, retries, dependencies, or concurrency are justified and documented.
