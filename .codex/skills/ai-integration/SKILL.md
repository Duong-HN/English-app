---
name: ai-integration
description: "Implement, change, test, or review LearnMate AI provider behavior. Use for backend/app/ai.py, backend/app/ai_schemas.py, Mock or Gemini adapters, prompts, structured output, provider configuration, AI failure handling, analysis feedback, or personalized learning-path generation."
---

# AI Integration

## Purpose

Maintain a replaceable, schema-validated AI layer that is deterministic in local tests, safe for learner data, and honest about the limits of text-based formative feedback.

## When to use

- Adding an analysis type, AI result field, provider method, prompt, model setting, or learning-path behavior.
- Integrating or debugging Gemini HTTP requests and structured JSON responses.
- Changing Mock AI output, provider selection, timeouts, error mapping, or AI tests.
- Reviewing privacy, pedagogical claims, or schema compatibility in AI-assisted features.

## Project-specific rules

- The backend uses a small AiProvider Protocol and build_provider factory in backend/app/ai.py, not a framework DI container, repository layer, Firebase, or a client-side AI SDK.
- Every protocol capability must be supported by both MockAiProvider and GeminiProvider before routes depend on it.
- Keep AI result models in backend/app/ai_schemas.py. Validate parsed provider output with Pydantic before persistence or response serialization.
- Gemini structured output must use generationConfig.responseJsonSchema. Tests explicitly ensure responseSchema is absent.
- Keep the Gemini API key server-side and send it in the x-goog-api-key header. Read model and timeout values from Settings.
- Use the deterministic mock provider for local development and API tests. Automated tests must not call a live AI service.
- Preserve the product boundary in backend/app/ai.py::_prompt and docs/ARCHITECTURE.md: AI scores are formative, never official IELTS results, and transcript text cannot establish pronunciation or accent quality.
- Learning-path prompts may receive recent aggregate counts, averages, and issue titles; do not send full historical learner submissions. backend/app/routers/learning_paths.py limits the profile to 20 recent analyses.
- Learning paths must pass LearningPathResult validation, contain exactly seven tasks, and have days 1 through 7 in order.
- Route-facing provider failures remain a generic HTTP 502. Do not leak API responses, keys, prompts, or internal validation details.

## Best practices

- Design the Pydantic schema first, then derive Gemini's JSON Schema from the model.
- Keep prompts explicit about language, allowed evidence, measurable output, and prohibited claims.
- Inject httpx.AsyncBaseTransport into GeminiProvider for deterministic MockTransport tests.
- Validate both the Gemini response and deterministic mock output against the same model.
- Keep current-input analysis separate from historical personalization; send only the minimum data needed.
- Use the configured timeout and test malformed payloads, HTTP failures, and schema-invalid content when changing parsing.
- Update the mock in the same change so the full app remains usable without a paid provider.

## Common mistakes

- Adding a method to AiProvider but only implementing Gemini or Mock.
- Using responseSchema instead of responseJsonSchema.
- Trusting JSON merely because the provider returned application/json.
- Persisting output before Pydantic validation.
- Making network calls in tests instead of using httpx.MockTransport.
- Putting GEMINI_API_KEY in mobile, admin, Postman, logs, URLs, or committed environment files.
- Claiming official exam equivalence or inferring acoustic pronunciation from a transcript.
- Sending full prior submissions to personalize a plan.
- Swallowing all context in tests so the actual request payload and prompt are never asserted.
- Adding an unsupported provider name and silently falling back instead of preserving build_provider's explicit error.

## Required workflow

1. Run git status --short and inspect backend/app/ai.py, ai_schemas.py, calling routers, settings, and current tests.
2. Define or revise the strict Pydantic result model, including bounds, list sizes, and cross-field validators.
3. Update the AiProvider protocol if the capability changes.
4. Implement and validate deterministic Mock output.
5. Implement Gemini using model_json_schema, responseJsonSchema, configured timeout, and server-side key handling.
6. Confirm routers persist only validated output and convert provider failures to the established generic 502 response.
7. Add async tests using httpx.MockTransport; assert request headers, generationConfig, prompt safety, parsing, and validation.
8. Run Ruff format, Ruff lint, and pytest from backend.
9. Update backend/.env.example, backend/README.md, docs/ARCHITECTURE.md, docs/API.md, docs/TEST_PLAN.md, and SECURITY.md only where behavior or configuration changed.
10. Review the final diff for learner-data minimization and prohibited claims.

## Examples from this repository

- backend/app/ai.py::AiProvider defines analyze and generate_learning_path as the shared adapter contract.
- backend/app/ai.py::MockAiProvider returns deterministic Vietnamese learning feedback and validates it.
- backend/app/ai.py::GeminiProvider._generate posts JSON Schema-constrained requests with httpx and parses the returned JSON text.
- backend/app/ai.py::GeminiProvider._prompt explicitly excludes pronunciation assessment for speaking transcripts.
- backend/app/ai_schemas.py::LearningPathResult.require_sequential_days enforces ordered days 1 through 7.
- backend/tests/test_ai.py uses httpx.MockTransport to assert x-goog-api-key and responseJsonSchema without external traffic.
- backend/app/routers/learning_paths.py::_activity_profile sends aggregates rather than historical input_text values.

## Files to reference

- backend/app/ai.py
- backend/app/ai_schemas.py
- backend/app/config.py
- backend/app/schemas.py
- backend/app/routers/analyses.py
- backend/app/routers/learning_paths.py
- backend/app/models.py
- backend/tests/test_ai.py
- backend/tests/test_api.py
- backend/tests/test_learning_paths.py
- backend/.env.example
- docs/ARCHITECTURE.md
- docs/API.md
- SECURITY.md

## Files that should never be modified

- Never modify backend/.env or commit GEMINI_API_KEY, live prompts containing learner data, access tokens, or provider response dumps.
- Never modify backend/*.db, backend/tests/*.db, backend/.venv/, caches, or bytecode.
- Never place provider secrets in mobile/, admin-dashboard/, postman/, generated client assets, or screenshots.
- Never overwrite unrelated dirty work; inspect the current worktree instead of embedding assumptions about which feature files are active.
- Do not edit a persisted historical migration merely because an AI JSON schema changed; create a migration only if the relational schema changes.

## Checklist before completion

- [ ] Protocol, Mock, Gemini, and caller behavior agree.
- [ ] Provider output is Pydantic-validated before use or persistence.
- [ ] Gemini uses responseJsonSchema, configured timeout, and a server-only key.
- [ ] Tests use MockTransport and make no live AI calls.
- [ ] Mock mode remains deterministic and functional.
- [ ] No official-score or transcript-pronunciation claim was introduced.
- [ ] Historical personalization exposes only necessary aggregates.
- [ ] Generic 502 handling and relevant docs/config remain accurate.
- [ ] Ruff and pytest pass without modifying generated or secret files.
