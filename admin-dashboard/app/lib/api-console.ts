import type { ApiConsoleMethod, ApiConsoleRequest } from "./api";

export type ApiPreset = {
  name: string;
  description: string;
  method: ApiConsoleMethod;
  path: string;
  body?: string;
};

export const API_PRESETS: ApiPreset[] = [
  {
    name: "Readiness",
    description: "Kiểm tra database và trạng thái sẵn sàng.",
    method: "GET",
    path: "/health/ready",
  },
  {
    name: "Tài khoản hiện tại",
    description: "Giải mã JWT đang đăng nhập.",
    method: "GET",
    path: "/api/v1/auth/me",
  },
  {
    name: "Thống kê quản trị",
    description: "Tổng hợp KPI vận hành dashboard.",
    method: "GET",
    path: "/api/v1/admin/stats",
  },
  {
    name: "Danh sách người dùng",
    description: "Phân trang 20 tài khoản đầu tiên.",
    method: "GET",
    path: "/api/v1/admin/users?limit=20&offset=0",
  },
  {
    name: "Danh sách phân tích",
    description: "Đọc các kết quả AI mới nhất.",
    method: "GET",
    path: "/api/v1/admin/analyses?limit=20&offset=0",
  },
  {
    name: "Danh sách lộ trình",
    description: "Đọc các lộ trình học cá nhân hóa mới nhất.",
    method: "GET",
    path: "/api/v1/admin/learning-paths?limit=20&offset=0",
  },
  {
    name: "Đăng ký học viên",
    description: "Kiểm tra luồng tạo tài khoản công khai.",
    method: "POST",
    path: "/api/v1/auth/register",
    body: JSON.stringify(
      {
        email: "learner@example.com",
        password: "ChangeMe123!",
        display_name: "Demo Learner",
      },
      null,
      2,
    ),
  },
  {
    name: "Chấm bài viết",
    description: "Tạo một lượt phân tích bằng provider đang cấu hình.",
    method: "POST",
    path: "/api/v1/analyses/writing",
    body: JSON.stringify(
      { input_text: "I have been learning English for three years." },
      null,
      2,
    ),
  },
  {
    name: "Tạo lộ trình 7 ngày",
    description: "Tạo lộ trình từ mục tiêu và lịch sử học của JWT hiện tại.",
    method: "POST",
    path: "/api/v1/learning-paths/generate",
    body: JSON.stringify(
      {
        goal: "Giao tiếp tự tin trong công việc",
        current_level: "B1",
        minutes_per_day: 30,
      },
      null,
      2,
    ),
  },
];

export function parseHeaderJson(value: string): Record<string, string> {
  if (!value.trim()) return {};
  let parsed: unknown;
  try {
    parsed = JSON.parse(value);
  } catch {
    throw new Error("Headers phải là một JSON object hợp lệ.");
  }
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error("Headers phải là một JSON object.");
  }
  return Object.fromEntries(
    Object.entries(parsed).map(([key, item]) => [key, String(item)]),
  );
}

function shellQuote(value: string) {
  return `'${value.replaceAll("'", `'\\''`)}'`;
}

export function buildCurl(baseUrl: string, request: ApiConsoleRequest) {
  const parts = [
    "curl",
    "--request",
    request.method,
    shellQuote(`${baseUrl}${request.path}`),
    "--header",
    shellQuote("Accept: application/json"),
    "--header",
    '"Authorization: Bearer $ADMIN_TOKEN"',
  ];
  for (const [key, value] of Object.entries(request.headers ?? {})) {
    if (key.toLowerCase() === "authorization") continue;
    parts.push("--header", shellQuote(`${key}: ${value}`));
  }
  if (request.body?.trim() && request.method !== "GET") {
    const hasContentType = Object.keys(request.headers ?? {}).some(
      (key) => key.toLowerCase() === "content-type",
    );
    if (!hasContentType) {
      parts.push("--header", shellQuote("Content-Type: application/json"));
    }
    parts.push("--data-raw", shellQuote(request.body.trim()));
  }
  return parts.join(" ");
}

export function formatBytes(value: number) {
  if (value < 1024) return `${value} B`;
  return `${(value / 1024).toFixed(1)} KB`;
}
