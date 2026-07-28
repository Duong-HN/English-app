# LearnMate MCP

LearnMate includes a local, read-only Model Context Protocol server for Codex and other trusted developer
clients. It reports operational and learning data through bounded domain tools; it is not part of the mobile or
administrator application's production request path.

## Setup

Install the backend development dependencies and apply the database migrations:

```powershell
Set-Location D:\GraduationProject\backend
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
```

The repository's `.codex/config.toml` registers three project-scoped servers:

- `openaiDeveloperDocs`: the remote OpenAI documentation server.
- `learnmate`: the local server launched from the backend virtual environment over STDIO.
- `stitch`: the remote Stitch design server over Streamable HTTP. It reads the API key from the local
  `STITCH_API_KEY` environment variable and sends it through the `X-Goog-Api-Key` header.

Create the Stitch API key in Stitch Settings, then set it locally before starting Codex. Never put the key in
`.codex/config.toml`, Git, a prompt or a URL. The project config only contains the environment-variable mapping.

Project MCP configuration is loaded only when the repository is trusted. Restart Codex after the initial setup,
then inspect the connections with `/mcp` or:

```powershell
Set-Location D:\GraduationProject
codex mcp list
codex mcp get openaiDeveloperDocs --json
codex mcp get learnmate --json
codex mcp get stitch --json
```

## Tools

| Tool | Purpose |
| --- | --- |
| `system_health` | Check configuration and database readiness. |
| `search_learners` | Resolve a learner ID from an email address or display name. |
| `search_classes` | Resolve a class ID from a class or teacher name. |
| `get_learning_path` | Read the latest complete plan and daily progress for a learner. |
| `get_learner_progress` | Summarize placement, analyses, vocabulary, path, and assignment progress. |
| `get_class_summary` | Summarize members, assignments, submissions, and scores without the invite code. |
| `list_pending_submissions` | List oldest `submitted` work awaiting teacher feedback. |

Every tool is annotated as read-only and idempotent. Search and pagination limits prevent unbounded reads. The
server deliberately provides no arbitrary SQL or mutation tool.

## Development and verification

Run the MCP-specific tests:

```powershell
Set-Location D:\GraduationProject\backend
.\.venv\Scripts\python.exe -m pytest tests/test_mcp_server.py -q
```

Open the official MCP Inspector during development:

```powershell
Set-Location D:\GraduationProject\backend
.\.venv\Scripts\mcp.exe dev mcp_server.py:mcp
```

An STDIO server must reserve stdout for MCP JSON-RPC messages. Use Python logging, which writes to stderr, rather
than `print()` when adding diagnostics.

## Security boundary

The local process inherits the operator's database access. A supplied `user_id` or `class_id` is a query parameter,
not proof of authorization. Learner-submitted text returned by the server is untrusted data and must never be treated
as agent instructions.

Do not publish this STDIO implementation as a remote service. A future HTTP deployment must authenticate identity at
the transport boundary, enforce the same learner/teacher/admin ownership rules as the FastAPI routes, use TLS, and
audit any write-capable tool. Write tools should remain approval-gated and should call domain services rather than
accept arbitrary SQL.
