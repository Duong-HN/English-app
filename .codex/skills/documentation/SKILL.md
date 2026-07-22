---
name: documentation
description: "Create and update LearnMate technical, API, testing, deployment, security, release, component, and Postman documentation so it matches the implemented repository. Use when behavior, contracts, architecture, configuration, workflows, supported platforms, safety boundaries, or versions change."
---

# Documentation

## Purpose

Keep documentation factual, navigable, synchronized with code/tests, and clear about implemented versus proposed capabilities.

## When to use

Use for feature docs, API changes, configuration/runbooks, architecture decisions, test plans, deployment/release changes, security notes, changelog/version work, or stale documentation fixes.

## Project-specific rules

- Use current source, tests, manifests, and workflows as evidence. Do not document a planned capability as implemented.
- Treat `README.md` as the product/repository entry point, component READMEs as local run guidance, and files under `docs/` as canonical detailed references.
- Treat `ideal.md` as the graduation proposal/history. Its Firebase, Cloud Functions, placement-test, and other aspirational material is not current runtime truth unless implemented elsewhere.
- Keep `docs/API.md` aligned with FastAPI paths, schemas, auth, query bounds, and status semantics.
- Keep `docs/ARCHITECTURE.md` aligned with actual data ownership and product boundaries.
- Keep `docs/TEST_PLAN.md` and `docs/DEPLOYMENT.md` aligned with scripts and GitHub Actions.
- Preserve security/safety statements: AI scores are formative, transcripts do not prove pronunciation, secrets stay server-side, and raw camera/audio is not stored.
- Use the current localization context accurately: learner/admin UI is Vietnamese-first, code identifiers/docs are mostly English, STT input locale is English.
- Update `CHANGELOG.md` and app versions together only for a real versioned change.

## Best practices

- Link to the most specific real file or command rather than duplicating large implementation details.
- Verify every command from the correct working directory and distinguish local development from production.
- Document required environment variable names without including values.
- State platform limitations explicitly, especially Android/iOS-only OCR and the lack of a production pronunciation pipeline.
- Keep diagrams consistent with the implemented FastAPI/PostgreSQL architecture.
- Update Postman README/collection descriptions when supported API workflows change.

## Common mistakes

- Copying Firebase or Cloud Functions claims from `ideal.md` into current architecture docs.
- Calling admin a normal Next server instead of Vinext/Vite/Cloudflare Worker.
- Claiming mobile desktop/web OCR support because scaffold folders exist.
- Publishing a Docker-internal dashboard API URL as a browser configuration.
- Showing real tokens, passwords, signing secrets, Gemini keys, or learner text in examples.
- Omitting migration, CORS, signing, audit, privacy, or manual production gaps.
- Updating only the root README while detailed docs and component READMEs become stale.

## Required workflow

1. Identify the implemented code/config/test evidence and the intended audience.
2. Select the canonical document: root/component README, API, architecture, test, deployment, Git, security, changelog, or Postman guide.
3. Cross-check names, paths, payloads, versions, commands, environment variables, and limitations against the current tree.
4. Edit the smallest complete set of documents and avoid redundant prose.
5. Validate Markdown structure, links, code fences, UTF-8 text, and command working directories.
6. Run relevant commands or tests when documentation asserts they work.
7. Inspect the final diff for secret leakage and contradictions across documents.

## Examples from this repository

- `README.md` explains the three-app monorepo and links the detailed docs.
- `docs/API.md` records learner and administrator routes plus ownership/error semantics.
- `docs/ARCHITECTURE.md` documents the OCR-to-API sequence, schema tables, RBAC, and transcript limitation.
- `docs/DEPLOYMENT.md` explains signed APKs, GHCR images, public dashboard URLs, hooks, and non-automatable cloud steps.
- `postman/README.md` explains safe local Current values while `backend/tests/test_postman_assets.py` enforces empty committed credentials.

## Files to reference

- `README.md`
- `backend/README.md`
- `mobile/README.md`
- `admin-dashboard/README.md`
- `docs/API.md`
- `docs/ARCHITECTURE.md`
- `docs/TEST_PLAN.md`
- `docs/DEPLOYMENT.md`
- `docs/GIT_WORKFLOW.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `postman/README.md`

## Files that should never be modified

- Never modify `ideal.md` as a side effect of runtime documentation work; change it only when the user explicitly requests the academic proposal.
- Never write real secret values, JWTs, passwords, learner submissions, keystore data, or personal machine paths into documentation.
- Never edit generated API/build output or dependency/vendor documentation in place.
- Never overwrite unrelated existing documentation work.

## Checklist before completion

- [ ] Every claim is supported by current code, tests, or configuration.
- [ ] Implemented and proposed behavior are clearly separated.
- [ ] Commands, paths, versions, variables, platforms, and status codes are correct.
- [ ] API, architecture, testing, deployment, security, component, and changelog docs remain consistent.
- [ ] Product-safety and privacy limitations are preserved.
- [ ] Links/formatting work and no secret or personal value is exposed.
