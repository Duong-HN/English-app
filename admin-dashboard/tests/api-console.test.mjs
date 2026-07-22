import assert from "node:assert/strict";
import test from "node:test";
import {
  API_PRESETS,
  buildCurl,
  formatBytes,
  parseHeaderJson,
} from "../app/lib/api-console.ts";
import { AdminApi, isManagementRole } from "../app/lib/api.ts";

test("ships useful presets for public and administrator endpoints", () => {
  const routes = API_PRESETS.map((item) => `${item.method} ${item.path}`);
  assert.ok(routes.includes("GET /health/ready"));
  assert.ok(routes.includes("GET /api/v1/admin/stats"));
  assert.ok(routes.includes("GET /api/v1/classes/managed?limit=20&offset=0"));
  assert.ok(routes.includes("POST /api/v1/auth/register"));
  assert.ok(routes.includes("POST /api/v1/analyses/writing"));
  assert.ok(routes.includes("GET /api/v1/admin/learning-paths?limit=20&offset=0"));
  assert.ok(routes.includes("POST /api/v1/learning-paths/generate"));
});

test("accepts management roles and rejects learner access in the client gate", () => {
  assert.equal(isManagementRole("admin"), true);
  assert.equal(isManagementRole("teacher"), true);
  assert.equal(isManagementRole("learner"), false);
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

test("requests learning paths with admin authorization and encoded filters", async () => {
  const originalFetch = globalThis.fetch;
  let capturedUrl = "";
  let capturedAuthorization = "";
  globalThis.fetch = async (input, init) => {
    capturedUrl = String(input);
    capturedAuthorization = new Headers(init?.headers).get("Authorization") ?? "";
    return Response.json({ items: [], total: 0 });
  };

  try {
    const api = new AdminApi("https://api.example.test/", "admin-jwt");
    const result = await api.learningPaths({ q: "job interview", limit: 25, offset: 25 });

    assert.equal(result.total, 0);
    assert.equal(
      capturedUrl,
      "https://api.example.test/api/v1/admin/learning-paths?q=job+interview&limit=25&offset=25",
    );
    assert.equal(capturedAuthorization, "Bearer admin-jwt");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("uses the exact classroom management paths, methods and snake_case bodies", async () => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (input, init) => {
    calls.push({
      url: String(input),
      method: init?.method ?? "GET",
      authorization: new Headers(init?.headers).get("Authorization"),
      body: init?.body ? JSON.parse(String(init.body)) : null,
    });
    return Response.json({ items: [], total: 0, join_code: "NEWCODE", updated_at: "2026-07-22T00:00:00Z" });
  };

  try {
    const api = new AdminApi("https://api.example.test", "teacher-jwt");
    await api.managedClasses({ limit: 20, offset: 40 });
    await api.createClass({
      name: "English B1",
      description: "Lớp buổi tối",
      target_level: "B1",
    });
    await api.updateClass("class-1", {
      name: "English B1 nâng cao",
      is_active: false,
    });
    await api.rotateClassJoinCode("class-1");
    await api.classMembers("class-1", { limit: 20, offset: 20 });
    await api.updateClassMember("class-1", "membership-1", "active");
    await api.classAssignments("class-1", { limit: 20, offset: 0 });
    await api.createClassAssignment("class-1", {
      title: "Viết email công việc",
      instructions: "Viết ít nhất 120 từ.",
      skill_type: "writing",
      target_level: "B1",
      due_at: "2026-08-01T10:00:00.000Z",
      status: "published",
    });
    await api.updateClassAssignment("assignment-1", {
      due_at: "2026-08-08T10:00:00.000Z",
      status: "closed",
    });
    await api.assignmentSubmissions("assignment-1", { limit: 20, offset: 0 });

    assert.deepEqual(
      calls.map(({ url, method }) => ({ url, method })),
      [
        { url: "https://api.example.test/api/v1/classes/managed?limit=20&offset=40", method: "GET" },
        { url: "https://api.example.test/api/v1/classes", method: "POST" },
        { url: "https://api.example.test/api/v1/classes/class-1", method: "PATCH" },
        { url: "https://api.example.test/api/v1/classes/class-1/join-code/rotate", method: "POST" },
        { url: "https://api.example.test/api/v1/classes/class-1/members?limit=20&offset=20", method: "GET" },
        { url: "https://api.example.test/api/v1/classes/class-1/members/membership-1", method: "PATCH" },
        { url: "https://api.example.test/api/v1/classes/class-1/assignments?limit=20&offset=0", method: "GET" },
        { url: "https://api.example.test/api/v1/classes/class-1/assignments", method: "POST" },
        { url: "https://api.example.test/api/v1/assignments/assignment-1", method: "PATCH" },
        { url: "https://api.example.test/api/v1/assignments/assignment-1/submissions?limit=20&offset=0", method: "GET" },
      ],
    );
    assert.ok(calls.every((call) => call.authorization === "Bearer teacher-jwt"));
    assert.deepEqual(calls[1].body, {
      name: "English B1",
      description: "Lớp buổi tối",
      target_level: "B1",
    });
    assert.deepEqual(calls[2].body, {
      name: "English B1 nâng cao",
      is_active: false,
    });
    assert.deepEqual(calls[5].body, { status: "active" });
    assert.deepEqual(calls[7].body, {
      title: "Viết email công việc",
      instructions: "Viết ít nhất 120 từ.",
      skill_type: "writing",
      target_level: "B1",
      due_at: "2026-08-01T10:00:00.000Z",
      status: "published",
    });
    assert.deepEqual(calls[8].body, {
      due_at: "2026-08-08T10:00:00.000Z",
      status: "closed",
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});
