"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  AdminAnalysis,
  AdminApi,
  AdminLearningPath,
  AdminStats,
  AdminUser,
  AssignmentSubmission,
  ApiError,
  AuditLog,
  ClassMember,
  SessionUser,
  TeacherAssignment,
  TeacherClass,
  normalizeBaseUrl,
} from "./lib/api";
import { ApiConsole } from "./api-console";

type Session = { token: string; user: SessionUser; baseUrl: string };
type View = "overview" | "users" | "analyses" | "paths" | "audit" | "console";

const TOKEN_KEY = "learnmate_admin_token";
const API_KEY = "learnmate_admin_api";
const PAGE_SIZE = 20;

const navItems: Array<{ id: View; label: string; short: string }> = [
  { id: "overview", label: "Tổng quan", short: "01" },
  { id: "users", label: "Người dùng", short: "02" },
  { id: "analyses", label: "Bài phân tích", short: "03" },
  { id: "paths", label: "Lộ trình học", short: "04" },
  { id: "audit", label: "Nhật ký quản trị", short: "05" },
  { id: "console", label: "API Console", short: "06" },
];

function formatDate(value: string | null, withTime = true) {
  if (!value) return "Chưa có";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  }).format(date);
}

function minimumLocalDeadline() {
  const date = new Date(Date.now() + 60_000);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function readableError(error: unknown) {
  if (error instanceof ApiError && error.status === 403) {
    return "Tài khoản hiện tại không có quyền thực hiện thao tác này.";
  }
  return error instanceof Error ? error.message : "Đã xảy ra lỗi không xác định.";
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function AdminApp({ defaultApiBaseUrl }: { defaultApiBaseUrl: string }) {
  const [session, setSession] = useState<Session | null>(null);
  const [restoring, setRestoring] = useState(true);

  useEffect(() => {
    const token = sessionStorage.getItem(TOKEN_KEY);
    const savedApi = sessionStorage.getItem(API_KEY) ?? defaultApiBaseUrl;
    const restoreSession = token
      ? new AdminApi(savedApi, token).me()
      : Promise.resolve<SessionUser | null>(null);

    restoreSession
      .then((user) => {
        if (!user || !token) return;
        if (user.role !== "admin" && user.role !== "teacher") {
          throw new Error("Tài khoản không có quyền truy cập cổng quản lý.");
        }
        setSession({ token, user, baseUrl: normalizeBaseUrl(savedApi) });
      })
      .catch(() => {
        sessionStorage.removeItem(TOKEN_KEY);
      })
      .finally(() => setRestoring(false));
  }, [defaultApiBaseUrl]);

  function acceptSession(next: Session) {
    sessionStorage.setItem(TOKEN_KEY, next.token);
    sessionStorage.setItem(API_KEY, next.baseUrl);
    setSession(next);
  }

  function logout() {
    sessionStorage.removeItem(TOKEN_KEY);
    setSession(null);
  }

  if (!session) {
    return (
      <LoginScreen
        defaultApiBaseUrl={defaultApiBaseUrl}
        restoring={restoring}
        onLogin={acceptSession}
      />
    );
  }
  return session.user.role === "teacher"
    ? <TeacherDashboard session={session} onLogout={logout} />
    : <Dashboard session={session} onLogout={logout} />;
}

function LoginScreen({
  defaultApiBaseUrl,
  restoring,
  onLogin,
}: {
  defaultApiBaseUrl: string;
  restoring: boolean;
  onLogin: (session: Session) => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [baseUrl, setBaseUrl] = useState(defaultApiBaseUrl);
  const [advanced, setAdvanced] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const normalized = normalizeBaseUrl(baseUrl);
      const api = new AdminApi(normalized);
      const response = await api.login(email.trim(), password);
      if (response.user.role !== "admin" && response.user.role !== "teacher") {
        throw new Error("Tài khoản học viên không thể truy cập cổng quản lý.");
      }
      onLogin({
        token: response.access_token,
        user: response.user,
        baseUrl: normalized,
      });
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-story" aria-label="Giới thiệu LearnMate Admin">
        <div className="brand brand-on-dark">
          <span className="brand-mark">LM</span>
          <span>
            <strong>LearnMate</strong>
            <small>Control room</small>
          </span>
        </div>
        <div className="story-copy">
          <p className="eyebrow">English learning operations</p>
          <h1>Quản lý lớp học AI bằng dữ liệu thật.</h1>
          <p>
            Theo dõi hoạt động học tập, bảo vệ tài khoản và kiểm duyệt phản hồi AI
            trong một không gian vận hành tập trung.
          </p>
        </div>
        <div className="story-metrics" aria-label="Khả năng của dashboard">
          <div><strong>RBAC</strong><span>Phân quyền tại API</span></div>
          <div><strong>Audit</strong><span>Theo vết thao tác</span></div>
          <div><strong>Live</strong><span>Số liệu trực tiếp</span></div>
        </div>
      </section>

      <section className="login-panel">
        <form className="login-card" onSubmit={submit}>
          <div className="mobile-brand brand">
            <span className="brand-mark">LM</span>
            <span><strong>LearnMate</strong><small>Control room</small></span>
          </div>
          <div>
            <p className="eyebrow blue">Khu vực quản trị</p>
            <h2>Đăng nhập hệ thống</h2>
            <p className="muted">Dành cho tài khoản giáo viên và quản trị viên.</p>
          </div>

          <label className="field">
            <span>Email giáo viên hoặc quản trị viên</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="admin@example.com"
              autoComplete="username"
              required
            />
          </label>
          <label className="field">
            <span>Mật khẩu</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Tối thiểu 8 ký tự"
              autoComplete="current-password"
              minLength={8}
              required
            />
          </label>

          <button
            className="advanced-toggle"
            type="button"
            aria-expanded={advanced}
            onClick={() => setAdvanced((value) => !value)}
          >
            {advanced ? "Ẩn cấu hình backend" : "Cấu hình backend"}
          </button>
          {advanced && (
            <label className="field compact-field">
              <span>Backend URL</span>
              <input
                type="url"
                value={baseUrl}
                onChange={(event) => setBaseUrl(event.target.value)}
                placeholder="http://127.0.0.1:8000"
                required
              />
            </label>
          )}

          {error && <div className="inline-alert error-alert" role="alert">{error}</div>}
          {restoring && !error && (
            <div className="inline-alert">Đang kiểm tra phiên đăng nhập trước…</div>
          )}

          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? "Đang xác thực…" : "Vào dashboard"}
          </button>
          <p className="login-footnote">
            Đăng ký công khai luôn tạo tài khoản học viên. Quản trị viên có thể cấp
            quyền giáo viên trong mục quản lý người dùng.
          </p>
        </form>
      </section>
    </main>
  );
}

function TeacherDashboard({ session, onLogout }: { session: Session; onLogout: () => void }) {
  const api = useMemo(
    () => new AdminApi(session.baseUrl, session.token),
    [session.baseUrl, session.token],
  );
  const [classes, setClasses] = useState<TeacherClass[]>([]);
  const [selectedClassId, setSelectedClassId] = useState<string | null>(null);
  const [members, setMembers] = useState<ClassMember[]>([]);
  const [assignments, setAssignments] = useState<TeacherAssignment[]>([]);
  const [selectedAssignmentId, setSelectedAssignmentId] = useState<string | null>(null);
  const [submissions, setSubmissions] = useState<AssignmentSubmission[]>([]);
  const [loading, setLoading] = useState(true);
  const [classLoading, setClassLoading] = useState(true);
  const [submissionLoading, setSubmissionLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadClasses = useCallback(async () => {
    const response = await api.classes();
    setClasses(response.items);
    setSelectedClassId((current) => current ?? response.items[0]?.id ?? null);
  }, [api]);

  useEffect(() => {
    let active = true;
    api.classes()
      .then((response) => {
        if (!active) return;
        setClasses(response.items);
        setSelectedClassId(response.items[0]?.id ?? null);
      })
      .catch((reason) => active && setError(readableError(reason)))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [api]);

  useEffect(() => {
    if (!selectedClassId) return;
    let active = true;
    Promise.all([
      api.classMembers(selectedClassId),
      api.classAssignments(selectedClassId),
    ])
      .then(([memberPage, assignmentPage]) => {
        if (!active) return;
        setMembers(memberPage.items);
        setAssignments(assignmentPage.items);
        setSubmissions([]);
        setSelectedAssignmentId(assignmentPage.items[0]?.id ?? null);
        setSubmissionLoading(assignmentPage.items.length > 0);
      })
      .catch((reason) => active && setError(readableError(reason)))
      .finally(() => active && setClassLoading(false));
    return () => { active = false; };
  }, [api, selectedClassId]);

  useEffect(() => {
    if (!selectedAssignmentId) return;
    let active = true;
    api.assignmentSubmissions(selectedAssignmentId)
      .then((response) => active && setSubmissions(response.items))
      .catch((reason) => active && setError(readableError(reason)))
      .finally(() => active && setSubmissionLoading(false));
    return () => { active = false; };
  }, [api, selectedAssignmentId]);

  const selectedClass = classes.find((item) => item.id === selectedClassId) ?? null;
  const selectedAssignment = assignments.find((item) => item.id === selectedAssignmentId) ?? null;

  function chooseClass(classId: string) {
    if (classId === selectedClassId) return;
    setSelectedClassId(classId);
    setMembers([]);
    setAssignments([]);
    setSelectedAssignmentId(null);
    setSubmissions([]);
    setClassLoading(true);
    setSubmissionLoading(false);
    setError(null);
  }

  function chooseAssignment(assignmentId: string) {
    if (assignmentId === selectedAssignmentId) return;
    setSelectedAssignmentId(assignmentId);
    setSubmissions([]);
    setSubmissionLoading(true);
    setError(null);
  }

  async function createClass(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const name = String(form.get("name") ?? "").trim();
    const description = String(form.get("description") ?? "").trim();
    if (!name) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const created = await api.createClass({
        name,
        ...(description ? { description } : {}),
      });
      formElement.reset();
      await loadClasses();
      chooseClass(created.id);
      setNotice(`Đã tạo lớp ${created.name}.`);
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setBusy(false);
    }
  }

  async function createAssignment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedClassId || classLoading) return;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const title = String(form.get("title") ?? "").trim();
    const content = String(form.get("content") ?? "").trim();
    const skill = String(form.get("skill") ?? "writing") as TeacherAssignment["skill"];
    const estimatedMinutes = Number(form.get("estimated_minutes") ?? 20);
    const dueValue = String(form.get("due_at") ?? "").trim();
    if (!title || !content || !dueValue) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const created = await api.createAssignment(selectedClassId, {
        title,
        content,
        skill,
        estimated_minutes: estimatedMinutes,
        due_at: new Date(dueValue).toISOString(),
      });
      formElement.reset();
      const response = await api.classAssignments(selectedClassId);
      setAssignments(response.items);
      chooseAssignment(created.id);
      setNotice(`Đã giao bài “${created.title}”.`);
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setBusy(false);
    }
  }

  async function saveFeedback(submissionId: string, feedback: string) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await api.updateSubmissionFeedback(submissionId, feedback);
      setSubmissions((items) => items.map((item) => item.id === updated.id ? updated : item));
      setNotice("Đã lưu nhận xét cho học viên.");
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="teacher-shell">
      <header className="teacher-topbar">
        <div className="brand">
          <span className="brand-mark">LM</span>
          <span><strong>LearnMate Teacher</strong><small>Không gian lớp học</small></span>
        </div>
        <div className="account-menu">
          <span className="avatar">{initials(session.user.display_name)}</span>
          <span className="account-copy"><strong>{session.user.display_name}</strong><small>{session.user.email}</small></span>
          <button type="button" className="ghost-button" onClick={onLogout}>Đăng xuất</button>
        </div>
      </header>

      <main className="teacher-content">
        <section className="section-heading">
          <div>
            <p className="eyebrow blue">Teacher workspace</p>
            <h1>Lớp học của tôi</h1>
            <p className="muted">Giao bài, theo dõi kết quả AI và phản hồi đúng phạm vi lớp phụ trách.</p>
          </div>
          <span className="count-badge">{classes.length} lớp</span>
        </section>

        {error && <div className="inline-alert error-alert" role="alert">{error}</div>}
        {notice && <div className="inline-alert success-alert" role="status">{notice}</div>}

        <section className="teacher-layout">
          <aside className="teacher-rail">
            <form className="panel teacher-form" onSubmit={createClass}>
              <div className="panel-heading"><div><p className="eyebrow">Lớp mới</p><h3>Tạo lớp học</h3></div></div>
              <label className="field"><span>Tên lớp</span><input name="name" required minLength={2} placeholder="IELTS Foundation" /></label>
              <label className="field"><span>Mô tả</span><textarea name="description" rows={3} placeholder="Thông tin ngắn cho học viên" /></label>
              <button className="primary-button" type="submit" disabled={busy || loading}>Tạo lớp</button>
            </form>

            <section className="panel class-picker">
              <div className="panel-heading"><div><p className="eyebrow">Danh sách</p><h3>Chọn lớp</h3></div></div>
              {loading ? <LoadingState label="Đang tải lớp…" /> : classes.length === 0 ? (
                <EmptyState message="Chưa có lớp. Hãy tạo lớp đầu tiên." />
              ) : classes.map((item) => (
                <button key={item.id} type="button" disabled={busy} aria-pressed={item.id === selectedClassId} className={item.id === selectedClassId ? "active" : ""} onClick={() => chooseClass(item.id)}>
                  <strong>{item.name}</strong><small>{item.member_count ?? 0} học viên · {item.invite_code ?? "chưa có mã"}</small>
                </button>
              ))}
            </section>
          </aside>

          <div className="teacher-workspace">
            {!selectedClass ? <EmptyState message="Chọn hoặc tạo một lớp để bắt đầu." /> : (
              <>
                <section className="panel class-hero">
                  <div><p className="eyebrow blue">Lớp đang chọn</p><h2>{selectedClass.name}</h2><p>{selectedClass.description || "Chưa có mô tả."}</p></div>
                  <div className="invite-code"><small>Mã tham gia</small><strong>{selectedClass.invite_code ?? "—"}</strong><span>Gửi mã này cho học viên</span></div>
                </section>

                <section className="teacher-grid">
                  <article className="panel teacher-list-panel">
                    <div className="panel-heading"><div><p className="eyebrow">Roster</p><h3>Học viên ({members.length})</h3></div></div>
                    {classLoading ? <LoadingState label="Đang tải học viên…" /> : members.length === 0 ? <EmptyState message="Chưa có học viên tham gia." /> : (
                      <div className="teacher-list">{members.map((member) => (
                        <div key={member.id}>
                          <span className="mini-avatar">{initials(member.display_name)}</span>
                          <span><strong>{member.display_name}</strong><small>{member.email}</small></span>
                          <b>{member.level ?? "—"}</b>
                        </div>
                      ))}</div>
                    )}
                  </article>

                  <form className="panel teacher-form" onSubmit={createAssignment}>
                    <div className="panel-heading"><div><p className="eyebrow">Assignment</p><h3>Giao bài mới</h3></div></div>
                    <label className="field"><span>Tiêu đề</span><input name="title" required minLength={3} placeholder="Viết đoạn giới thiệu bản thân" /></label>
                    <label className="field"><span>Yêu cầu</span><textarea name="content" rows={4} required placeholder="Nội dung học viên cần thực hiện" /></label>
                    <div className="teacher-form-row">
                      <label className="field"><span>Kỹ năng</span><select name="skill" defaultValue="writing"><option value="reading">Reading</option><option value="writing">Writing</option><option value="speaking">Speaking</option></select></label>
                      <label className="field"><span>Số phút</span><input name="estimated_minutes" type="number" min={5} max={120} defaultValue={20} required /></label>
                    </div>
                    <label className="field"><span>Hạn nộp</span><input name="due_at" type="datetime-local" min={minimumLocalDeadline()} required /></label>
                    <button className="primary-button" type="submit" disabled={busy || classLoading}>Giao bài</button>
                  </form>
                </section>

                <section className="panel assignments-panel">
                  <div className="panel-heading"><div><p className="eyebrow">Class work</p><h3>Bài tập đã giao</h3></div><span className="count-badge">{assignments.length}</span></div>
                  {classLoading ? <LoadingState label="Đang tải bài tập…" /> : assignments.length === 0 ? <EmptyState message="Chưa có bài tập nào." /> : (
                    <div className="assignment-tabs">{assignments.map((item) => (
                      <button type="button" key={item.id} disabled={busy} aria-pressed={item.id === selectedAssignmentId} className={item.id === selectedAssignmentId ? "active" : ""} onClick={() => chooseAssignment(item.id)}>
                        <span className={`type-badge ${item.skill}`}>{item.skill}</span><strong>{item.title}</strong><small>{item.estimated_minutes} phút · {item.due_at ? `hạn ${formatDate(item.due_at)}` : "không hạn nộp"}</small>
                      </button>
                    ))}</div>
                  )}
                </section>

                {selectedAssignment && (
                  <section className="panel submissions-panel">
                    <div className="panel-heading"><div><p className="eyebrow">Review</p><h3>Bài nộp · {selectedAssignment.title}</h3></div><span className="count-badge">{submissions.length}</span></div>
                    {submissionLoading ? <LoadingState label="Đang tải bài nộp…" /> : submissions.length === 0 ? <EmptyState message="Chưa có học viên nộp bài." /> : (
                      <div className="submission-list">{submissions.map((submission) => (
                        <SubmissionReview key={submission.id} submission={submission} busy={busy} onSave={saveFeedback} />
                      ))}</div>
                    )}
                  </section>
                )}
              </>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

function SubmissionReview({
  submission,
  busy,
  onSave,
}: {
  submission: AssignmentSubmission;
  busy: boolean;
  onSave: (submissionId: string, feedback: string) => Promise<void>;
}) {
  const [feedback, setFeedback] = useState(submission.teacher_feedback ?? "");
  return (
    <article className="submission-card">
      <header>
        <div><strong>{submission.learner_name}</strong><small>{submission.learner_id}</small></div>
        <span className="provider-badge">{submission.analysis?.score == null ? submission.status : `${submission.analysis.score}/10`}</span>
      </header>
      {submission.input_text && <p>{submission.input_text}</p>}
      {submission.analysis?.result && <details><summary>Xem phản hồi AI</summary><pre>{JSON.stringify(submission.analysis.result, null, 2)}</pre></details>}
      <label className="field"><span>Nhận xét của giáo viên</span><textarea rows={3} value={feedback} onChange={(event) => setFeedback(event.target.value)} placeholder="Điểm tốt và điều cần sửa…" /></label>
      <button type="button" className="secondary-button" disabled={busy || !feedback.trim()} onClick={() => void onSave(submission.id, feedback.trim())}>Lưu nhận xét</button>
    </article>
  );
}

function Dashboard({ session, onLogout }: { session: Session; onLogout: () => void }) {
  const [view, setView] = useState<View>("overview");
  const [healthy, setHealthy] = useState<boolean | null>(null);
  const api = useMemo(
    () => new AdminApi(session.baseUrl, session.token),
    [session.baseUrl, session.token],
  );

  useEffect(() => {
    let active = true;
    const check = () =>
      api
        .health()
        .then(() => active && setHealthy(true))
        .catch(() => active && setHealthy(false));
    void check();
    const timer = window.setInterval(check, 30_000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [api]);

  const title = navItems.find((item) => item.id === view)?.label ?? "Dashboard";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand brand-on-dark sidebar-brand">
          <span className="brand-mark">LM</span>
          <span><strong>LearnMate</strong><small>Control room</small></span>
        </div>
        <nav className="side-nav" aria-label="Điều hướng quản trị">
          {navItems.map((item) => (
            <button
              type="button"
              key={item.id}
              className={view === item.id ? "active" : ""}
              onClick={() => setView(item.id)}
              data-testid={`nav-${item.id}`}
            >
              <span>{item.short}</span>{item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-status">
          <span className={`status-dot ${healthy === false ? "down" : ""}`} />
          <div><strong>{healthy === false ? "Backend gián đoạn" : "Backend online"}</strong><small>{session.baseUrl}</small></div>
        </div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <div>
            <p className="breadcrumb">LearnMate / Quản trị</p>
            <h1>{title}</h1>
          </div>
          <div className="account-menu">
            <span className="avatar">{initials(session.user.display_name)}</span>
            <span className="account-copy"><strong>{session.user.display_name}</strong><small>{session.user.email}</small></span>
            <button type="button" className="ghost-button" onClick={onLogout}>Đăng xuất</button>
          </div>
        </header>

        <nav className="mobile-nav" aria-label="Điều hướng trên thiết bị nhỏ">
          {navItems.map((item) => (
            <button
              type="button"
              key={item.id}
              className={view === item.id ? "active" : ""}
              onClick={() => setView(item.id)}
            >{item.label}</button>
          ))}
        </nav>

        <main className="content-area">
          {view === "overview" && <OverviewPage api={api} onNavigate={setView} />}
          {view === "users" && <UsersPage api={api} currentUser={session.user} />}
          {view === "analyses" && <AnalysesPage api={api} />}
          {view === "paths" && <LearningPathsPage api={api} />}
          {view === "audit" && <AuditPage api={api} />}
          {view === "console" && <ApiConsole api={api} baseUrl={session.baseUrl} />}
        </main>
      </div>
    </div>
  );
}

function OverviewPage({ api, onNavigate }: { api: AdminApi; onNavigate: (view: View) => void }) {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([api.stats(), api.auditLogs(5)])
      .then(([statsData, logData]) => {
        if (!active) return;
        setStats(statsData);
        setLogs(logData.items);
      })
      .catch((reason) => active && setError(readableError(reason)));
    return () => { active = false; };
  }, [api]);

  if (error) return <ErrorState message={error} />;
  if (!stats) return <LoadingState label="Đang tổng hợp dữ liệu vận hành…" />;

  const maxTrend = Math.max(1, ...stats.analyses_last_7_days.map((item) => item.count));
  const totalByType = Math.max(1, Object.values(stats.analyses_by_type).reduce((a, b) => a + b, 0));
  const cards = [
    { label: "Tổng người dùng", value: stats.total_users, note: `+${stats.new_users_last_7_days} trong 7 ngày`, tone: "blue" },
    { label: "Đang hoạt động", value: stats.active_users, note: `${stats.admin_users} quản trị viên`, tone: "green" },
    { label: "Lượt phân tích", value: stats.total_analyses, note: `${stats.analyses_today} lượt hôm nay`, tone: "purple" },
    { label: "Lộ trình học", value: stats.total_learning_paths, note: `${stats.learning_paths_today} lộ trình hôm nay`, tone: "amber" },
  ];

  return (
    <div className="page-stack">
      <section className="welcome-row">
        <div><p className="eyebrow blue">Live operations</p><h2>Hệ thống đang vận hành ổn định.</h2><p className="muted">Số liệu được lấy trực tiếp từ backend, không dùng dữ liệu mẫu.</p></div>
        <button className="secondary-button" type="button" onClick={() => onNavigate("users")}>Quản lý người dùng</button>
      </section>

      <section className="metric-grid" aria-label="Chỉ số tổng quan">
        {cards.map((card) => (
          <article className={`metric-card tone-${card.tone}`} key={card.label}>
            <span className="metric-accent" /><p>{card.label}</p><strong>{card.value}</strong><small>{card.note}</small>
          </article>
        ))}
      </section>

      <section className="dashboard-grid">
        <article className="panel trend-panel">
          <div className="panel-heading"><div><p className="eyebrow">7 ngày gần nhất</p><h3>Nhịp độ học tập</h3></div><span className="panel-chip">{stats.total_analyses} tổng lượt</span></div>
          <div className="trend-chart" aria-label="Biểu đồ lượt phân tích bảy ngày">
            {stats.analyses_last_7_days.map((item) => (
              <div className="trend-column" key={item.date}>
                <span className="trend-value">{item.count}</span>
                <div className="trend-track"><span style={{ height: `${Math.max(7, (item.count / maxTrend) * 100)}%` }} /></div>
                <small>{new Date(`${item.date}T00:00:00`).toLocaleDateString("vi-VN", { weekday: "short" })}</small>
              </div>
            ))}
          </div>
        </article>

        <article className="panel type-panel">
          <div className="panel-heading"><div><p className="eyebrow">Cơ cấu nội dung</p><h3>Loại bài học</h3></div></div>
          <div className="type-list">
            {[{ key: "reading", label: "Đọc hiểu", className: "reading" }, { key: "writing", label: "Viết", className: "writing" }, { key: "speaking", label: "Luyện nói", className: "speaking" }].map((item) => {
              const count = stats.analyses_by_type[item.key] ?? 0;
              return <div className="type-row" key={item.key}><div><span className={`type-dot ${item.className}`} /><strong>{item.label}</strong><small>{count} lượt</small></div><div className="progress-track"><span className={item.className} style={{ width: `${(count / totalByType) * 100}%` }} /></div></div>;
            })}
          </div>
          <button className="text-button" type="button" onClick={() => onNavigate("analyses")}>Xem toàn bộ bài phân tích →</button>
        </article>
      </section>

      <section className="panel activity-panel">
        <div className="panel-heading"><div><p className="eyebrow">Kiểm soát thay đổi</p><h3>Hoạt động quản trị gần đây</h3></div><button className="text-button" type="button" onClick={() => onNavigate("audit")}>Xem nhật ký</button></div>
        {logs.length === 0 ? <EmptyState message="Chưa có thao tác quản trị nào." /> : <div className="activity-list">{logs.map((log) => <AuditRow log={log} key={log.id} />)}</div>}
      </section>
    </div>
  );
}

function UsersPage({ api, currentUser }: { api: AdminApi; currentUser: SessionUser }) {
  const [query, setQuery] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [role, setRole] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(0);
  const [reload, setReload] = useState(0);
  const [data, setData] = useState<{ items: AdminUser[]; total: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api.users({ q: appliedQuery, role, isActive: status, limit: PAGE_SIZE, offset: page * PAGE_SIZE })
      .then((result) => {
        if (!active) return;
        setError(null);
        setData(result);
      })
      .catch((reason) => active && setError(readableError(reason)));
    return () => { active = false; };
  }, [api, appliedQuery, role, status, page, reload]);

  function search(event: FormEvent) {
    event.preventDefault();
    setPage(0);
    setAppliedQuery(query.trim());
    setReload((value) => value + 1);
  }

  async function updateUser(user: AdminUser, update: { is_active?: boolean; role?: string }, message: string) {
    if (!window.confirm(message)) return;
    setBusyId(user.id);
    setNotice(null);
    setError(null);
    try {
      await api.updateUser(user.id, update);
      setNotice("Đã cập nhật tài khoản và ghi vào audit log.");
      setReload((value) => value + 1);
    } catch (reason) {
      setError(readableError(reason));
    } finally {
      setBusyId(null);
    }
  }

  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / PAGE_SIZE));

  return (
    <div className="page-stack">
      <section className="section-heading"><div><p className="eyebrow blue">Identity & access</p><h2>Quản lý người dùng</h2><p className="muted">Tìm kiếm, phân quyền và khóa tài khoản ngay tại API.</p></div><span className="count-badge">{data?.total ?? 0} tài khoản</span></section>
      <form className="filter-bar" onSubmit={search}>
        <label className="search-field"><span className="sr-only">Tìm người dùng</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tìm theo tên hoặc email…" /></label>
        <select aria-label="Lọc vai trò" value={role} onChange={(event) => { setRole(event.target.value); setPage(0); }}><option value="">Mọi vai trò</option><option value="learner">Học viên</option><option value="teacher">Giáo viên</option><option value="admin">Quản trị viên</option></select>
        <select aria-label="Lọc trạng thái" value={status} onChange={(event) => { setStatus(event.target.value); setPage(0); }}><option value="">Mọi trạng thái</option><option value="true">Đang hoạt động</option><option value="false">Đã khóa</option></select>
        <button className="secondary-button" type="submit">Tìm kiếm</button>
      </form>
      {notice && <div className="inline-alert success-alert">{notice}</div>}
      {error && <div className="inline-alert error-alert" role="alert">{error}</div>}
      {!data ? <LoadingState label="Đang tải danh sách người dùng…" /> : data.items.length === 0 ? <EmptyState message="Không tìm thấy tài khoản phù hợp." /> : (
        <section className="table-card">
          <div className="data-table user-table" role="table" aria-label="Danh sách người dùng">
            <div className="table-row table-head" role="row"><span>Người dùng</span><span>Vai trò</span><span>Hoạt động</span><span>Đăng nhập cuối</span><span>Trạng thái</span><span>Thao tác</span></div>
            {data.items.map((user) => (
              <div className="table-row" role="row" key={user.id}>
                <div className="user-cell"><span className="mini-avatar">{initials(user.display_name)}</span><span><strong>{user.display_name}</strong><small>{user.email}</small></span></div>
                <div><select aria-label={`Vai trò của ${user.email}`} value={user.role} disabled={busyId === user.id || user.id === currentUser.id} onChange={(event) => void updateUser(user, { role: event.target.value }, `Đổi vai trò ${user.email} thành ${event.target.value}?`)}><option value="learner">Học viên</option><option value="teacher">Giáo viên</option><option value="admin">Admin</option></select></div>
                <div><strong>{user.analysis_count}</strong><small className="cell-note"> bài phân tích</small></div>
                <div className="date-cell">{formatDate(user.last_login_at)}</div>
                <div><span className={`status-pill ${user.is_active ? "active" : "locked"}`}>{user.is_active ? "Hoạt động" : "Đã khóa"}</span></div>
                <div><button className="row-button" type="button" disabled={busyId === user.id || user.id === currentUser.id} onClick={() => void updateUser(user, { is_active: !user.is_active }, `${user.is_active ? "Khóa" : "Mở lại"} tài khoản ${user.email}?`)}>{busyId === user.id ? "Đang lưu…" : user.is_active ? "Khóa" : "Mở lại"}</button></div>
              </div>
            ))}
          </div>
          <Pagination page={page} totalPages={totalPages} onChange={setPage} />
        </section>
      )}
    </div>
  );
}

function AnalysesPage({ api }: { api: AdminApi }) {
  const [query, setQuery] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [type, setType] = useState("");
  const [page, setPage] = useState(0);
  const [reload, setReload] = useState(0);
  const [data, setData] = useState<{ items: AdminAnalysis[]; total: number } | null>(null);
  const [selected, setSelected] = useState<AdminAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api.analyses({ q: appliedQuery, type, limit: PAGE_SIZE, offset: page * PAGE_SIZE })
      .then((result) => active && setData(result))
      .catch((reason) => active && setError(readableError(reason)));
    return () => { active = false; };
  }, [api, appliedQuery, type, page, reload]);

  function search(event: FormEvent) {
    event.preventDefault();
    setPage(0);
    setAppliedQuery(query.trim());
    setReload((value) => value + 1);
  }

  async function remove(item: AdminAnalysis) {
    if (!window.confirm("Xóa bài phân tích này? Thao tác sẽ được ghi audit log.")) return;
    try {
      await api.deleteAnalysis(item.id);
      setSelected(null);
      setReload((value) => value + 1);
    } catch (reason) {
      setError(readableError(reason));
    }
  }

  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / PAGE_SIZE));
  return (
    <div className="page-stack">
      <section className="section-heading"><div><p className="eyebrow blue">Content review</p><h2>Bài phân tích AI</h2><p className="muted">Kiểm tra đầu vào, kết quả có cấu trúc và nhà cung cấp AI.</p></div><span className="count-badge">{data?.total ?? 0} bản ghi</span></section>
      <form className="filter-bar" onSubmit={search}>
        <label className="search-field"><span className="sr-only">Tìm bài phân tích</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tìm nội dung hoặc email…" /></label>
        <select aria-label="Lọc loại bài" value={type} onChange={(event) => { setType(event.target.value); setPage(0); }}><option value="">Mọi loại bài</option><option value="reading">Đọc hiểu</option><option value="writing">Viết</option><option value="speaking">Luyện nói</option></select>
        <button className="secondary-button" type="submit">Tìm kiếm</button>
      </form>
      {error && <div className="inline-alert error-alert" role="alert">{error}</div>}
      {!data ? <LoadingState label="Đang tải dữ liệu phân tích…" /> : data.items.length === 0 ? <EmptyState message="Không có bài phân tích phù hợp." /> : (
        <section className="analysis-grid">
          {data.items.map((item) => (
            <article className="analysis-card" key={item.id}>
              <div className="analysis-card-top"><span className={`type-badge ${item.type}`}>{item.type === "reading" ? "Đọc hiểu" : item.type === "writing" ? "Viết" : "Luyện nói"}</span><span className="provider-badge">{item.provider}</span></div>
              <h3>{item.input_text}</h3>
              <div className="analysis-owner"><span className="mini-avatar">{initials(item.user_display_name)}</span><span><strong>{item.user_display_name}</strong><small>{item.user_email}</small></span></div>
              <div className="analysis-meta"><span>{formatDate(item.created_at)}</span><strong>{item.score === null ? "Không điểm" : `${item.score}/10`}</strong></div>
              <button className="card-link" type="button" onClick={() => setSelected(item)}>Xem chi tiết</button>
            </article>
          ))}
          <div className="full-span"><Pagination page={page} totalPages={totalPages} onChange={setPage} /></div>
        </section>
      )}
      {selected && <AnalysisDialog item={selected} onClose={() => setSelected(null)} onDelete={() => void remove(selected)} />}
    </div>
  );
}

function AnalysisDialog({ item, onClose, onDelete }: { item: AdminAnalysis; onClose: () => void; onDelete: () => void }) {
  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="detail-dialog" role="dialog" aria-modal="true" aria-labelledby="analysis-dialog-title">
        <header><div><p className="eyebrow blue">Analysis detail</p><h2 id="analysis-dialog-title">Chi tiết bài phân tích</h2></div><button className="close-button" type="button" onClick={onClose} aria-label="Đóng chi tiết">×</button></header>
        <div className="detail-facts"><span><small>Học viên</small><strong>{item.user_email}</strong></span><span><small>Loại bài</small><strong>{item.type}</strong></span><span><small>Provider</small><strong>{item.provider}</strong></span><span><small>Điểm</small><strong>{item.score ?? "—"}</strong></span></div>
        <div className="detail-section"><h3>Đầu vào học viên</h3><p>{item.input_text}</p></div>
        <div className="detail-section"><h3>Kết quả có cấu trúc</h3><pre>{JSON.stringify(item.result, null, 2)}</pre></div>
        <footer><button className="danger-button" type="button" onClick={onDelete}>Xóa bản ghi</button><button className="secondary-button" type="button" onClick={onClose}>Đóng</button></footer>
      </section>
    </div>
  );
}

function LearningPathsPage({ api }: { api: AdminApi }) {
  const [query, setQuery] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [page, setPage] = useState(0);
  const [reload, setReload] = useState(0);
  const [data, setData] = useState<{ items: AdminLearningPath[]; total: number } | null>(null);
  const [selected, setSelected] = useState<AdminLearningPath | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api.learningPaths({ q: appliedQuery, limit: PAGE_SIZE, offset: page * PAGE_SIZE })
      .then((result) => { if (active) { setData(result); setError(null); } })
      .catch((reason) => active && setError(readableError(reason)));
    return () => { active = false; };
  }, [api, appliedQuery, page, reload]);

  function search(event: FormEvent) {
    event.preventDefault();
    setPage(0);
    setAppliedQuery(query.trim());
    setReload((value) => value + 1);
  }

  async function remove(item: AdminLearningPath) {
    if (!window.confirm("Xóa lộ trình này? Thao tác sẽ được ghi audit log.")) return;
    try {
      await api.deleteLearningPath(item.id);
      setSelected(null);
      setReload((value) => value + 1);
    } catch (reason) {
      setError(readableError(reason));
    }
  }

  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / PAGE_SIZE));
  return (
    <div className="page-stack">
      <section className="section-heading"><div><p className="eyebrow blue">Personalized learning</p><h2>Lộ trình học 7 ngày</h2><p className="muted">Theo dõi mục tiêu, mức độ cá nhân hóa và nhiệm vụ mà học viên nhận được.</p></div><span className="count-badge">{data?.total ?? 0} lộ trình</span></section>
      <form className="filter-bar path-filter" onSubmit={search}>
        <label className="search-field"><span className="sr-only">Tìm lộ trình</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tìm theo mục tiêu, tên hoặc email…" /></label>
        <button className="secondary-button" type="submit">Tìm kiếm</button>
      </form>
      {error && <div className="inline-alert error-alert" role="alert">{error}</div>}
      {!data ? <LoadingState label="Đang tải lộ trình học…" /> : data.items.length === 0 ? <EmptyState message="Chưa có lộ trình học phù hợp." /> : (
        <section className="analysis-grid">
          {data.items.map((item) => (
            <article className="analysis-card path-card" key={item.id}>
              <div className="analysis-card-top"><span className="type-badge path">{item.current_level}</span><span className="provider-badge">{item.provider}</span></div>
              <h3>{item.goal}</h3>
              <p className="path-summary">{item.plan.summary}</p>
              <div className="analysis-owner"><span className="mini-avatar">{initials(item.user_display_name)}</span><span><strong>{item.user_display_name}</strong><small>{item.user_email}</small></span></div>
              <div className="analysis-meta"><span>{formatDate(item.created_at)}</span><strong>{item.minutes_per_day} phút/ngày</strong></div>
              <button className="card-link" type="button" onClick={() => setSelected(item)}>Xem 7 nhiệm vụ</button>
            </article>
          ))}
          <div className="full-span"><Pagination page={page} totalPages={totalPages} onChange={setPage} /></div>
        </section>
      )}
      {selected && <LearningPathDialog item={selected} onClose={() => setSelected(null)} onDelete={() => void remove(selected)} />}
    </div>
  );
}

function LearningPathDialog({ item, onClose, onDelete }: { item: AdminLearningPath; onClose: () => void; onDelete: () => void }) {
  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="detail-dialog" role="dialog" aria-modal="true" aria-labelledby="path-dialog-title">
        <header><div><p className="eyebrow blue">Learning path detail</p><h2 id="path-dialog-title">{item.goal}</h2></div><button className="close-button" type="button" onClick={onClose} aria-label="Đóng chi tiết">×</button></header>
        <div className="detail-facts"><span><small>Học viên</small><strong>{item.user_email}</strong></span><span><small>Trình độ</small><strong>{item.current_level}</strong></span><span><small>Thời lượng</small><strong>{item.minutes_per_day} phút/ngày</strong></span><span><small>Provider</small><strong>{item.provider}</strong></span></div>
        <div className="detail-section"><h3>Mục tiêu tuần</h3><p>{item.plan.weekly_goal}</p></div>
        <div className="detail-section"><h3>Trọng tâm cá nhân hóa</h3><div className="path-chips">{item.plan.focus_areas.map((focus) => <span key={focus}>{focus}</span>)}</div></div>
        <div className="detail-section"><h3>Nhiệm vụ từng ngày</h3><ol className="path-task-list">{item.plan.daily_tasks.map((task) => <li key={task.day}><span>{task.day}</span><div><strong>{task.title} · {task.duration_minutes} phút</strong><p>{task.activity}</p><small>Đạt khi: {task.success_criteria}</small></div></li>)}</ol></div>
        <footer><button className="danger-button" type="button" onClick={onDelete}>Xóa lộ trình</button><button className="secondary-button" type="button" onClick={onClose}>Đóng</button></footer>
      </section>
    </div>
  );
}

function AuditPage({ api }: { api: AdminApi }) {
  const [logs, setLogs] = useState<AuditLog[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => {
    return api.auditLogs(100)
      .then((data) => {
        setError(null);
        setLogs(data.items);
      })
      .catch((reason) => setError(readableError(reason)));
  }, [api]);
  useEffect(() => { void load(); }, [load]);

  function refresh() {
    setLogs(null);
    setError(null);
    void load();
  }

  return (
    <div className="page-stack">
      <section className="section-heading"><div><p className="eyebrow blue">Audit trail</p><h2>Nhật ký quản trị</h2><p className="muted">Mọi thay đổi nhạy cảm đều có người thực hiện, đối tượng và thời điểm.</p></div><button className="secondary-button" type="button" onClick={refresh}>Làm mới</button></section>
      {error && <div className="inline-alert error-alert" role="alert">{error}</div>}
      {!logs ? <LoadingState label="Đang đọc nhật ký…" /> : logs.length === 0 ? <EmptyState message="Chưa có hoạt động quản trị." /> : <section className="panel audit-list">{logs.map((log) => <AuditRow log={log} key={log.id} expanded />)}</section>}
    </div>
  );
}

function AuditRow({ log, expanded = false }: { log: AuditLog; expanded?: boolean }) {
  const labels: Record<string, string> = { "user.updated": "Cập nhật người dùng", "analysis.deleted": "Xóa bài phân tích", "learning_path.deleted": "Xóa lộ trình học" };
  return (
    <div className={`audit-row ${expanded ? "expanded" : ""}`}>
      <span className="audit-mark">{log.action.startsWith("user") ? "U" : "A"}</span>
      <div className="audit-copy"><strong>{labels[log.action] ?? log.action}</strong><span>{log.admin_email ?? "Quản trị viên đã xóa"} · {formatDate(log.created_at)}</span>{expanded && <code>{JSON.stringify(log.details)}</code>}</div>
      <span className="audit-target">{log.target_type}<small>{log.target_id?.slice(0, 8) ?? "—"}</small></span>
    </div>
  );
}

function Pagination({ page, totalPages, onChange }: { page: number; totalPages: number; onChange: (page: number) => void }) {
  return <div className="pagination"><button type="button" disabled={page === 0} onClick={() => onChange(page - 1)}>← Trước</button><span>Trang {page + 1} / {totalPages}</span><button type="button" disabled={page + 1 >= totalPages} onClick={() => onChange(page + 1)}>Sau →</button></div>;
}

function LoadingState({ label }: { label: string }) {
  return <div className="state-card loading-state" role="status"><span className="loading-pulse" /><strong>{label}</strong></div>;
}

function ErrorState({ message }: { message: string }) {
  return <div className="state-card error-state" role="alert"><strong>Không thể tải dữ liệu</strong><span>{message}</span></div>;
}

function EmptyState({ message }: { message: string }) {
  return <div className="state-card empty-state"><span className="empty-mark">LM</span><strong>{message}</strong></div>;
}
