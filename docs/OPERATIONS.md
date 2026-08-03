# Operations runbook

## Request tracing and metrics

Every API response contains `X-Request-ID`. A caller-provided ID is accepted only when it contains safe correlation
characters and is at most 128 characters; otherwise the API generates a UUID. The API logs a compact JSON event with
request ID, method, route template, status and latency. Passwords, JWTs, AI keys and learner text are not logged.

`GET /metrics` exposes Prometheus text for request counts and duration sums. It is intentionally low-cardinality and
does not claim to provide p95/p99 by itself; scrape it from every API replica and derive histograms at the gateway or
instrumentation layer. Add alerts for 5xx rate, latency, queue age/depth, AI timeout/retry rate, database pool
exhaustion, Redis failures, authentication failures and storage failures.

## Media storage

The demo default is `MEDIA_STORAGE_BACKEND=local`. Production must set `MEDIA_STORAGE_BACKEND=s3`,
`OBJECT_STORAGE_BUCKET`, `OBJECT_STORAGE_REGION` and credentials through the platform secret manager. The S3 adapter
uses generated object keys, uploads through a temporary file with a size limit, stores only the object key in the
database and serves short-lived presigned URLs. The bucket must be private, encrypted, versioned and protected by a
lifecycle policy for orphaned objects.

An S3-compatible endpoint can be supplied with `OBJECT_STORAGE_ENDPOINT_URL`. A CDN must be configured in front of the
private bucket with origin protection and a reviewed signed-delivery policy; putting a public bucket URL in the API is
not an acceptable CDN configuration.

## Backup and restore

The repository provides scripts, but it does not create a backup service or cloud credentials. Set an explicit RPO/RTO
with the owner. A conservative starting target for a small prototype is daily database backup, 30-day retention, RPO
24 hours and RTO 4 hours. Production should use managed PostgreSQL PITR plus object-storage versioning/replication.

Create a database dump and SHA-256 manifest:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://backup-user:password@db.example/learnmate"
.\scripts\backup-db.ps1 -OutputDirectory .\backups
```

Run a destructive restore drill only against an isolated disposable database:

```powershell
$env:RESTORE_DATABASE_URL = "postgresql+psycopg://restore-user:password@restore-db/learnmate_restore"
$env:RESTORE_CONFIRMATION = "YES"
.\scripts\restore-drill.ps1 -BackupFile .\backups\learnmate-YYYYMMDD-HHMMSS.dump
```

Record backup duration, restore duration, migration version, row counts and a sample authenticated read. A backup that
has never been restored is not evidence of recoverability.

## Deployment gate

The release workflow builds immutable-tagged images and the deployment workflow calls externally configured hooks. The
workflow now fails when a production hook is missing; a green GitHub build alone is not a production deployment. The
platform owner must provide a separate migration job, managed PostgreSQL/Redis/object storage, TLS, secrets, worker
scaling, health checks, alert routing and rollback rehearsal.
