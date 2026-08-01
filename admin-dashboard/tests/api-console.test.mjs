import assert from "node:assert/strict";
import test from "node:test";
import {
  API_PRESETS,
  buildCurl,
  formatBytes,
  parseHeaderJson,
} from "../app/lib/api-console.ts";
import { AdminApi } from "../app/lib/api.ts";

test("ships useful presets for public and administrator endpoints", () => {
  const routes = API_PRESETS.map((item) => `${item.method} ${item.path}`);
  assert.ok(routes.includes("GET /health/ready"));
  assert.ok(routes.includes("GET /api/v1/admin/stats"));
  assert.ok(routes.includes("POST /api/v1/auth/register"));
  assert.ok(routes.includes("GET /api/v1/admin/analysis-jobs?limit=20&offset=0"));
  assert.ok(routes.includes("GET /api/v1/admin/learning-paths?limit=20&offset=0"));
  assert.ok(routes.includes("POST /api/v1/learning-paths/generate"));
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

test("reviews teacher applications through the administrator API", async () => {
  const originalFetch = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (input, init) => {
    requests.push({ url: String(input), method: init?.method ?? "GET", body: init?.body, headers: new Headers(init?.headers) });
    if ((init?.method ?? "GET") === "GET") {
      return Response.json({ items: [], total: 0 });
    }
    return Response.json({
      id: "application-1",
      user_id: "learner-1",
      motivation: "I have taught English for several years.",
      organization: null,
      status: "approved",
      review_note: "Approved.",
      requested_at: "2026-07-22T00:00:00Z",
      reviewed_at: "2026-07-23T00:00:00Z",
      applicant_email: "learner@example.com",
      applicant_display_name: "Learner",
      reviewer_email: "admin@example.com",
    });
  };

  try {
    const api = new AdminApi("https://api.example.test", "admin-jwt");
    const listed = await api.teacherApplications({ status: "pending", limit: 20, offset: 0 });
    const reviewed = await api.reviewTeacherApplication("application-1", "approved", "Approved.");

    assert.equal(listed.total, 0);
    assert.equal(reviewed.status, "approved");
    assert.equal(requests[0].url, "https://api.example.test/api/v1/admin/teacher-applications?status=pending&limit=20&offset=0");
    assert.equal(requests[0].headers.get("Authorization"), "Bearer admin-jwt");
    assert.equal(requests[1].method, "PATCH");
    assert.deepEqual(JSON.parse(requests[1].body), { status: "approved", review_note: "Approved." });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("teacher API creates a class and sends feedback with bearer authorization", async () => {
  const originalFetch = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (input, init) => {
    requests.push({ url: String(input), method: init?.method ?? "GET", body: init?.body, headers: new Headers(init?.headers) });
    if (String(input).endsWith("/api/v1/classes")) {
      return Response.json({
        id: "class-1",
        teacher_id: "teacher-1",
        name: "IELTS Foundation",
        description: null,
        invite_code: "ABC123",
        created_at: "2026-07-22T00:00:00Z",
      }, { status: 201 });
    }
    if (String(input).endsWith("/api/v1/classes/class-1/assignments")) {
      return Response.json({
        id: "assignment-1",
        class_id: "class-1",
        class_name: "IELTS Foundation",
        created_by_id: "teacher-1",
        title: "Write an introduction",
        skill: "writing",
        content: "Write 120 words.",
        estimated_minutes: 20,
        due_at: "2026-08-01T00:00:00Z",
        created_at: "2026-07-22T00:00:00Z",
      }, { status: 201 });
    }
    return Response.json({
      id: "submission-1",
      assignment_id: "assignment-1",
      learner_id: "learner-1",
      status: "reviewed",
      teacher_feedback: "Bố cục rõ ràng.",
      submitted_at: "2026-07-22T00:00:00Z",
    });
  };

  try {
    const api = new AdminApi("https://api.example.test", "teacher-jwt");
    await api.createClass({ name: "IELTS Foundation" });
    await api.createAssignment("class-1", {
      title: "Write an introduction",
      content: "Write 120 words.",
      skill: "writing",
      estimated_minutes: 20,
      due_at: "2026-08-01T00:00:00Z",
    });
    await api.updateSubmissionFeedback("submission-1", "Bố cục rõ ràng.");

    assert.equal(requests[0].url, "https://api.example.test/api/v1/classes");
    assert.equal(requests[0].method, "POST");
    assert.equal(requests[0].headers.get("Authorization"), "Bearer teacher-jwt");
    assert.deepEqual(JSON.parse(requests[0].body), { name: "IELTS Foundation" });
    assert.equal(requests[1].url, "https://api.example.test/api/v1/classes/class-1/assignments");
    assert.deepEqual(JSON.parse(requests[1].body), {
      title: "Write an introduction",
      content: "Write 120 words.",
      skill: "writing",
      estimated_minutes: 20,
      due_at: "2026-08-01T00:00:00Z",
    });
    assert.equal(
      requests[2].url,
      "https://api.example.test/api/v1/submissions/submission-1/feedback",
    );
    assert.equal(requests[2].method, "PATCH");
    assert.deepEqual(JSON.parse(requests[2].body), { feedback: "Bố cục rõ ràng." });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("turns FastAPI validation details into a readable message", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => Response.json(
    { detail: [{ msg: "due_at must be in the future" }] },
    { status: 422 },
  );

  try {
    const api = new AdminApi("https://api.example.test", "teacher-jwt");
    await assert.rejects(
      api.createAssignment("class-1", {
        title: "Expired task",
        content: "Write a paragraph.",
        skill: "writing",
        estimated_minutes: 20,
        due_at: "2020-01-01T00:00:00Z",
      }),
      /due_at must be in the future/,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
