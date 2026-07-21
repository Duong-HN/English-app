import assert from "node:assert/strict";
import test from "node:test";
import {
  API_PRESETS,
  buildCurl,
  formatBytes,
  parseHeaderJson,
} from "../app/lib/api-console.ts";

test("ships useful presets for public and administrator endpoints", () => {
  const routes = API_PRESETS.map((item) => `${item.method} ${item.path}`);
  assert.ok(routes.includes("GET /health/ready"));
  assert.ok(routes.includes("GET /api/v1/admin/stats"));
  assert.ok(routes.includes("POST /api/v1/auth/register"));
  assert.ok(routes.includes("POST /api/v1/analyses/writing"));
});

test("parses custom headers and rejects non-object values", () => {
  assert.deepEqual(parseHeaderJson('{"X-Debug": true, "X-Trace": 42}'), {
    "X-Debug": "true",
    "X-Trace": "42",
  });
  assert.deepEqual(parseHeaderJson(""), {});
  assert.throws(() => parseHeaderJson("[]"), /JSON object/);
  assert.throws(() => parseHeaderJson("{broken"), /hợp lệ/);
});

test("creates a reproducible curl command without copying the live JWT", () => {
  const command = buildCurl("https://api.example.com", {
    method: "POST",
    path: "/api/v1/analyses/writing",
    headers: { Authorization: "private-token", "X-Trace": "demo" },
    body: '{"input_text":"Hello world"}',
  });

  assert.match(command, /https:\/\/api\.example\.com\/api\/v1\/analyses\/writing/);
  assert.match(command, /Authorization: Bearer \$ADMIN_TOKEN/);
  assert.match(command, /Content-Type: application\/json/);
  assert.match(command, /X-Trace: demo/);
  assert.doesNotMatch(command, /private-token/);
  assert.match(command, /input_text/);
});

test("formats response sizes", () => {
  assert.equal(formatBytes(512), "512 B");
  assert.equal(formatBytes(1536), "1.5 KB");
});
