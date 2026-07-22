---
name: database
description: "Design, migrate, query, test, or review LearnMate persistence. Use for SQLAlchemy models and sessions, Alembic revisions, SQLite/PostgreSQL compatibility, relational constraints, indexes, ownership-safe queries, transactions, JSON persistence, database health, or deployment schema changes."
---

# Database

## Purpose

Keep LearnMate's SQLAlchemy models, Alembic history, queries, and deployment schema consistent across SQLite development/tests and PostgreSQL production.

## When to use

- Adding or changing a persisted entity, column, relationship, constraint, index, or JSON field.
- Creating, reviewing, applying, or debugging Alembic migrations.
- Changing SQLAlchemy queries, pagination, transactions, session behavior, or readiness checks.
- Investigating data isolation, integrity, query performance, or SQLite/PostgreSQL differences.

## Project-specific rules

- The backend is a pragmatic modular monolith. FastAPI routers issue SQLAlchemy 2 queries directly; there is no Repository Pattern, Unit of Work layer, Clean Architecture data gateway, Firebase, or Firestore.
- Define typed ORM entities with Mapped and mapped_column in backend/app/models.py, using the shared Base from backend/app/db.py.
- Use string UUID primary keys and UTC timestamps via models.utc_now, matching current User, Analysis, LearningPath, and AdminAuditLog models.
- Keep models and Alembic revisions synchronized. Applied/released migrations are immutable; add the next sequential revision.
- SQLite is for local development and tests; PostgreSQL is the production/Compose target. Keep SQL, defaults, JSON, date handling, and constraints portable.
- Preserve normalize_database_url for postgres:// and postgresql:// URLs and the psycopg driver.
- Keep ownership foreign keys indexed. User deletion cascades analyses and learning paths; deleting an admin sets admin_audit_logs.admin_user_id to null so audit records survive.
- Validate AI-owned JSON with backend/app/ai_schemas.py before persisting it.
- Production uses Alembic with AUTO_CREATE_SCHEMA=false. Base.metadata.create_all is only a local/test convenience.
- Learner CRUD must filter by authenticated user_id. Cross-user queries belong only in require_admin-protected routes.
- Use explicit commits, refresh returned entities after inserts/updates, and roll back handled transaction failures such as registration uniqueness races.

## Best practices

- Start from the closest model and migration pair and ensure types, nullability, lengths, foreign keys, delete behavior, defaults, and indexes match.
- Generate migrations with Alembic autogenerate, then review and simplify the operations by hand.
- Give every migration a working downgrade unless a documented, deliberate irreversible change is required.
- Bound list queries and order histories by created_at descending. Existing public/admin limits are capped at 100.
- Aggregate in SQL where practical, as admin stats and analysis-count subqueries do, instead of loading entire tables.
- Limit AI personalization reads; learning paths use only 20 recent analyses.
- Test a clean migration on an empty database independently of application schema auto-creation.
- Consider both data authorization and SQL correctness during query review.

## Common mistakes

- Editing only models.py or only an Alembic revision.
- Rewriting 0001, 0002, or another already-applied revision instead of adding a new revision.
- Testing only through AUTO_CREATE_SCHEMA=true and missing a broken migration chain.
- Using SQLite-specific behavior that fails on PostgreSQL.
- Forgetting an ownership filter, foreign-key index, ondelete rule, or relationship back_populates.
- Persisting unvalidated provider JSON.
- Calling commit after a caught IntegrityError without rollback.
- Loading all rows for history, personalization, or admin pages.
- Assuming ORM cascade configuration replaces the database foreign-key action.
- Committing a local .db file as a fixture or migration artifact.

## Required workflow

1. Run git status --short; inspect backend/app/models.py, db.py, relevant routers/schemas/tests, alembic/env.py, and every existing revision.
2. Write down the intended schema and data behavior, including nullability, defaults, uniqueness, indexes, ownership, and deletion.
3. Update the ORM model and relationships.
4. Create the next Alembic revision. Review both upgrade and downgrade against the model rather than accepting autogenerate blindly.
5. Update Pydantic contracts and direct router queries as required. Preserve authenticated user filters.
6. Add tests for persistence, constraints, ordering/pagination, deletion, isolation, and admin access where applicable.
7. Run Ruff format, Ruff lint, and pytest from backend.
8. Against a fresh temporary database, set AUTO_CREATE_SCHEMA=false and run python -m alembic upgrade head; confirm alembic current reports head.
9. When practical, exercise the feature with PostgreSQL through docker-compose.yml.
10. Update docs/ARCHITECTURE.md, docs/API.md, backend/README.md, and docs/DEPLOYMENT.md if the schema or operating procedure changed.

## Examples from this repository

- backend/app/db.py::normalize_database_url and _engine configure psycopg/PostgreSQL, SQLite thread handling, pool_pre_ping, and SessionLocal.
- backend/app/models.py::User defines indexed identity fields and relationships with delete-orphan ORM cascades.
- backend/app/models.py::Analysis and LearningPath use user_id foreign keys with ondelete=CASCADE and indexed created_at histories.
- backend/app/models.py::AdminAuditLog uses ondelete=SET NULL to preserve audit history after administrator deletion.
- backend/alembic/versions/0001_initial.py creates users and analyses; 0002_admin_console.py evolves users and adds audit logs; 0003_learning_paths.py adds persisted plans.
- backend/app/routers/admin.py::list_users uses a grouped subquery and outer join to avoid per-user count queries.
- backend/app/routers/health.py::readiness performs SELECT 1 and maps database failure to 503.

## Files to reference

- backend/app/db.py
- backend/app/models.py
- backend/app/schemas.py
- backend/app/ai_schemas.py
- backend/app/routers/analyses.py
- backend/app/routers/learning_paths.py
- backend/app/routers/admin.py
- backend/app/routers/health.py
- backend/alembic/env.py
- backend/alembic/script.py.mako
- backend/alembic/versions/
- backend/alembic.ini
- backend/tests/conftest.py
- docker-compose.yml
- backend/Dockerfile
- docs/ARCHITECTURE.md

## Files that should never be modified

- Never modify local/generated databases: backend/*.db, backend/tests/*.db, Compose volume contents, or ad hoc migration test databases.
- Never modify backend/.env, backend/.venv/, __pycache__/, .pytest_cache/, .ruff_cache/, or *.pyc.
- Never rewrite an Alembic revision already applied or released. Inspect `git status` and preserve any unrelated migration work actually present.
- Never alter production data, credentials, or a deployment database during local verification.
- Never discard unrelated dirty work to make a migration diff look clean.

## Checklist before completion

- [ ] ORM model and new migration agree on every schema detail.
- [ ] Upgrade and downgrade are reviewed and the revision chain is linear.
- [ ] SQLite and PostgreSQL compatibility was considered.
- [ ] Ownership, foreign keys, deletion behavior, and indexes are correct.
- [ ] JSON content is validated before persistence.
- [ ] Transactions commit, refresh, and roll back appropriately.
- [ ] Queries remain bounded and avoid obvious N+1 behavior.
- [ ] Tests and a clean AUTO_CREATE_SCHEMA=false upgrade pass.
- [ ] No local database, historical migration, secret, cache, or unrelated change was touched.
