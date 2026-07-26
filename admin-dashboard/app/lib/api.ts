export type AdminUser = {
  id: string;
  email: string;
  display_name: string;
  role: "learner" | "teacher" | "admin";
  level: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
  last_login_at: string | null;
  analysis_count: number;
};

export type TeacherClass = {
  id: string;
  teacher_id: string;
  name: string;
  description: string | null;
  invite_code: string | null;
  member_count?: number;
  created_at: string;
};

export type ClassMember = {
  id: string;
  user_id?: string;
  learner_id?: string;
  email: string;
  display_name: string;
  level: string | null;
  joined_at: string;
};

export type TeacherAssignment = {
  id: string;
  class_id: string;
  title: string;
  content: string;
  skill: "reading" | "writing" | "speaking";
  estimated_minutes: number;
  due_at: string;
  created_at: string;
};

export type AssignmentSubmission = {
  id: string;
  assignment_id: string;
  learner_id: string;
  learner_name: string;
  status: string;
  input_text?: string;
  analysis?: {
    result: Record<string, unknown>;
    score: number | null;
  } | null;
  teacher_feedback: string | null;
  submitted_at: string | null;
  feedback_at?: string | null;
};

export type SessionUser = Omit<
  AdminUser,
  "analysis_count" | "updated_at" | "last_login_at"
>;

export type AdminStats = {
  total_users: number;
  active_users: number;
  admin_users: number;
  new_users_last_7_days: number;
  total_analyses: number;
  analyses_today: number;
  total_learning_paths: number;
  learning_paths_today: number;
  analyses_by_type: Record<string, number>;
  analyses_last_7_days: Array<{ date: string; count: number }>;
};

export type AdminAnalysis = {
  id: string;
  user_id: string;
  user_email: string;
  user_display_name: string;
  type: "reading" | "writing" | "speaking";
  input_text: string;
  result: Record<string, unknown>;
  score: number | null;
  provider: string;
  created_at: string;
};

export type LearningPathTask = {
  day: number;
  title: string;
  skill: string;
  activity: string;
  duration_minutes: number;
  success_criteria: string;
};

export type AdminLearningPath = {
  id: string;
  user_id: string;
  user_email: string;
  user_display_name: string;
  goal: string;
  current_level: "A1" | "A2" | "B1" | "B2" | "C1";
  minutes_per_day: number;
  plan: {
    summary: string;
    weekly_goal: string;
    focus_areas: string[];
    personalization_notes: string[];
    daily_tasks: LearningPathTask[];
    checkpoints: string[];
  };
  provider: string;
  created_at: string;
};

export type AuditLog = {
  id: string;
  admin_user_id: string | null;
  admin_email: string | null;
  action: string;
  target_type: string;
  target_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
};

export type ApiConsoleMethod = "GET" | "POST" | "PATCH" | "DELETE";

export type ApiConsoleRequest = {
  method: ApiConsoleMethod;
  path: string;
  headers?: Record<string, string>;
  body?: string;
};

export type ApiConsoleResponse = {
  status: number;
  statusText: string;
  ok: boolean;
  durationMs: number;
  sizeBytes: number;
  headers: Record<string, string>;
  body: unknown;
  rawBody: string;
};

type Page<T> = { items: T[]; total: number };

function apiErrorDetail(body: unknown, status: number): string {
  if (typeof body !== "object" || body === null || !("detail" in body)) {
    return `API trả về HTTP ${status}`;
  }
  const detail = (body as { detail: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (typeof item === "object" && item !== null && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return null;
      })
      .filter((item): item is string => Boolean(item));
    if (messages.length) return messages.join(" · ");
  }
  return `API trả về HTTP ${status}`;
}

export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export function normalizeBaseUrl(value: string): string {
  const candidate = value.trim().replace(/\/+$/, "");
  let parsed: URL;
  try {
    parsed = new URL(candidate);
  } catch {
    throw new Error("Backend URL phải là một địa chỉ http hoặc https hợp lệ.");
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error("Backend URL chỉ hỗ trợ giao thức http hoặc https.");
  }
  return candidate;
}

function queryString(values: Record<string, string | number | boolean | null | undefined>) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }
  const result = params.toString();
  return result ? `?${result}` : "";
}

export class AdminApi {
  readonly baseUrl: string;
  private readonly token?: string;

  constructor(baseUrl: string, token?: string) {
    this.baseUrl = normalizeBaseUrl(baseUrl);
    this.token = token;
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (init.body) headers.set("Content-Type", "application/json");
    if (this.token) headers.set("Authorization", `Bearer ${this.token}`);

    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, { ...init, headers });
    } catch (error) {
      throw new ApiError(
        error instanceof Error ? error.message : "Không thể kết nối backend.",
        0,
        null,
      );
    }

    const contentType = response.headers.get("content-type") ?? "";
    const body: unknown = contentType.includes("application/json")
      ? await response.json()
      : await response.text();
    if (!response.ok) {
      throw new ApiError(apiErrorDetail(body, response.status), response.status, body);
    }
    return body as T;
  }

  async consoleRequest(request: ApiConsoleRequest): Promise<ApiConsoleResponse> {
    const path = request.path.trim();
    if (!path.startsWith("/") || path.startsWith("//")) {
      throw new Error("Đường dẫn API phải bắt đầu bằng một dấu / và không được là URL bên ngoài.");
    }

    const backend = new URL(this.baseUrl);
    const target = new URL(path, `${backend.origin}/`);
    if (target.origin !== backend.origin) {
      throw new Error("API Console chỉ được gọi backend đang cấu hình.");
    }

    const headers = new Headers(request.headers);
    headers.set("Accept", "application/json");
    if (this.token) headers.set("Authorization", `Bearer ${this.token}`);
    const body = request.body?.trim();
    if (body && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    const startedAt = performance.now();
    let response: Response;
    try {
      response = await fetch(target, {
        method: request.method,
        headers,
        body: request.method === "GET" ? undefined : body || undefined,
      });
    } catch (error) {
      throw new ApiError(
        error instanceof Error ? error.message : "Không thể kết nối backend.",
        0,
        null,
      );
    }

    const rawBody = await response.text();
    let parsedBody: unknown = rawBody;
    if ((response.headers.get("content-type") ?? "").includes("application/json")) {
      try {
        parsedBody = rawBody ? JSON.parse(rawBody) : null;
      } catch {
        parsedBody = rawBody;
      }
    }

    return {
      status: response.status,
      statusText: response.statusText,
      ok: response.ok,
      durationMs: Math.round(performance.now() - startedAt),
      sizeBytes: new TextEncoder().encode(rawBody).length,
      headers: Object.fromEntries([...response.headers.entries()].sort()),
      body: parsedBody,
      rawBody,
    };
  }

  login(email: string, password: string) {
    return this.request<{ access_token: string; user: SessionUser }>(
      "/api/v1/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ email, password }),
      },
    );
  }

  me() {
    return this.request<SessionUser>("/api/v1/auth/me");
  }

  health() {
    return this.request<{ status: string }>("/health/ready");
  }

  stats() {
    return this.request<AdminStats>("/api/v1/admin/stats");
  }

  users(filters: {
    q?: string;
    role?: string;
    isActive?: string;
    limit?: number;
    offset?: number;
  }) {
    return this.request<Page<AdminUser>>(
      `/api/v1/admin/users${queryString({
        q: filters.q,
        role: filters.role,
        is_active: filters.isActive,
        limit: filters.limit,
        offset: filters.offset,
      })}`,
    );
  }

  updateUser(userId: string, update: { is_active?: boolean; role?: string }) {
    return this.request<AdminUser>(`/api/v1/admin/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(update),
    });
  }

  classes() {
    return this.request<Page<TeacherClass>>("/api/v1/classes");
  }

  createClass(input: { name: string; description?: string }) {
    return this.request<TeacherClass>("/api/v1/classes", {
      method: "POST",
      body: JSON.stringify(input),
    });
  }

  classMembers(classId: string) {
    return this.request<Page<ClassMember>>(
      `/api/v1/classes/${encodeURIComponent(classId)}/members`,
    );
  }

  classAssignments(classId: string) {
    return this.request<Page<TeacherAssignment>>(
      `/api/v1/classes/${encodeURIComponent(classId)}/assignments`,
    );
  }

  createAssignment(
    classId: string,
    input: {
      title: string;
      content: string;
      skill: "reading" | "writing" | "speaking";
      estimated_minutes: number;
      due_at: string;
    },
  ) {
    return this.request<TeacherAssignment>(
      `/api/v1/classes/${encodeURIComponent(classId)}/assignments`,
      { method: "POST", body: JSON.stringify(input) },
    );
  }

  assignmentSubmissions(assignmentId: string) {
    return this.request<Page<AssignmentSubmission>>(
      `/api/v1/assignments/${encodeURIComponent(assignmentId)}/submissions`,
    );
  }

  updateSubmissionFeedback(submissionId: string, teacherFeedback: string) {
    return this.request<AssignmentSubmission>(
      `/api/v1/submissions/${encodeURIComponent(submissionId)}/feedback`,
      {
        method: "PATCH",
        body: JSON.stringify({ feedback: teacherFeedback }),
      },
    );
  }

  analyses(filters: {
    q?: string;
    type?: string;
    limit?: number;
    offset?: number;
  }) {
    return this.request<Page<AdminAnalysis>>(
      `/api/v1/admin/analyses${queryString(filters)}`,
    );
  }

  deleteAnalysis(analysisId: string) {
    return this.request<{ message: string }>(
      `/api/v1/admin/analyses/${analysisId}`,
      { method: "DELETE" },
    );
  }

  learningPaths(filters: { q?: string; limit?: number; offset?: number }) {
    return this.request<Page<AdminLearningPath>>(
      `/api/v1/admin/learning-paths${queryString(filters)}`,
    );
  }

  deleteLearningPath(learningPathId: string) {
    return this.request<{ message: string }>(
      `/api/v1/admin/learning-paths/${learningPathId}`,
      { method: "DELETE" },
    );
  }

  auditLogs(limit = 50) {
    return this.request<Page<AuditLog>>(
      `/api/v1/admin/audit-logs${queryString({ limit })}`,
    );
  }
}
