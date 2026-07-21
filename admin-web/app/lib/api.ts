export type AdminUser = {
  id: string;
  email: string;
  display_name: string;
  role: "learner" | "admin";
  level: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
  last_login_at: string | null;
  analysis_count: number;
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

type Page<T> = { items: T[]; total: number };

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body: unknown,
  ) {
    super(message);
    this.name = "ApiError";
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

  constructor(baseUrl: string, private readonly token?: string) {
    this.baseUrl = normalizeBaseUrl(baseUrl);
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
      const detail =
        typeof body === "object" && body !== null && "detail" in body
          ? String((body as { detail: unknown }).detail)
          : `API trả về HTTP ${response.status}`;
      throw new ApiError(detail, response.status, body);
    }
    return body as T;
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

  auditLogs(limit = 50) {
    return this.request<Page<AuditLog>>(
      `/api/v1/admin/audit-logs${queryString({ limit })}`,
    );
  }
}
