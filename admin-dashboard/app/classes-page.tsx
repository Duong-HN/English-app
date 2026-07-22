"use client";

import { FormEvent, useEffect, useState } from "react";
import { AdminApi } from "./lib/api";
import type {
  AnalysisType,
  AssignmentCreateInput,
  AssignmentSubmission,
  AssignmentUpdateInput,
  CefrLevel,
  ClassAssignment,
  ClassCreateInput,
  ClassMember,
  ClassUpdateInput,
  ManagedClass,
  SessionUser,
} from "./lib/api";

const PAGE_SIZE = 20;
const LEVELS: CefrLevel[] = ["A1", "A2", "B1", "B2", "C1"];
const SKILLS: AnalysisType[] = ["reading", "writing", "speaking"];

type PageData<T> = { items: T[]; total: number };

function readableClassError(reason: unknown) {
  return reason instanceof Error
    ? reason.message
    : "Đã xảy ra lỗi khi xử lý dữ liệu lớp học.";
}

function formatDateTime(value: string | null) {
  if (!value) return "Chưa đặt";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function toDateTimeLocal(value: string | null) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return localDate.toISOString().slice(0, 16);
}

function assignmentStatusLabel(assignment: ClassAssignment) {
  if (assignment.status === "closed") return "Đã đóng";
  if (assignment.due_at && new Date(assignment.due_at).getTime() <= Date.now()) {
    return "Quá hạn";
  }
  return "Đang mở";
}

function skillLabel(skill: AnalysisType) {
  return {
    reading: "Đọc hiểu",
    writing: "Viết",
    speaking: "Luyện nói",
  }[skill];
}

function membershipLabel(status: ClassMember["status"]) {
  return {
    pending: "Chờ duyệt",
    active: "Đang học",
    removed: "Đã rời lớp",
  }[status];
}

function ManagementPagination({
  page,
  total,
  onChange,
}: {
  page: number;
  total: number;
  onChange: (page: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (total === 0) return null;
  return (
    <div className="pagination" aria-label="Phân trang dữ liệu lớp học">
      <button
        type="button"
        disabled={page === 0}
        onClick={() => onChange(page - 1)}
      >
        ← Trước
      </button>
      <span>
        Trang {page + 1} / {totalPages}
      </span>
      <button
        type="button"
        disabled={page + 1 >= totalPages}
        onClick={() => onChange(page + 1)}
      >
        Sau →
      </button>
    </div>
  );
}

export function ClassesPage({
  api,
  currentUser,
}: {
  api: AdminApi;
  currentUser: SessionUser;
}) {
  const [data, setData] = useState<PageData<ManagedClass> | null>(null);
  const [page, setPage] = useState(0);
  const [reload, setReload] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [selectedClass, setSelectedClass] = useState<ManagedClass | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [targetLevel, setTargetLevel] = useState<"" | CefrLevel>("");

  useEffect(() => {
    let active = true;
    api
      .managedClasses({ limit: PAGE_SIZE, offset: page * PAGE_SIZE })
      .then((result) => {
        if (!active) return;
        setData(result);
        setError(null);
        setSelectedClass((current) => {
          if (!current) return current;
          return result.items.find((item) => item.id === current.id) ?? current;
        });
      })
      .catch((reason) => active && setError(readableClassError(reason)))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [api, page, reload]);

  function refreshClasses() {
    setLoading(true);
    setReload((value) => value + 1);
  }

  function changePage(nextPage: number) {
    setLoading(true);
    setPage(nextPage);
  }

  function replaceClass(updated: ManagedClass) {
    setData((current) =>
      current
        ? {
            ...current,
            items: current.items.map((item) =>
              item.id === updated.id ? updated : item,
            ),
          }
        : current,
    );
    setSelectedClass((current) =>
      current?.id === updated.id ? updated : current,
    );
  }

  async function createClass(event: FormEvent) {
    event.preventDefault();
    const payload: ClassCreateInput = {
      name: name.trim(),
      description: description.trim(),
      target_level: targetLevel || null,
    };
    setBusyAction("create");
    setError(null);
    setNotice(null);
    try {
      const created = await api.createClass(payload);
      setName("");
      setDescription("");
      setTargetLevel("");
      setPage(0);
      setSelectedClass(created);
      setNotice(`Đã tạo lớp “${created.name}” và cấp mã tham gia.`);
      refreshClasses();
    } catch (reason) {
      setError(readableClassError(reason));
    } finally {
      setBusyAction(null);
    }
  }

  async function updateClass(item: ManagedClass, input: ClassUpdateInput) {
    setBusyAction(`update:${item.id}`);
    setError(null);
    setNotice(null);
    try {
      const updated = await api.updateClass(item.id, input);
      replaceClass(updated);
      setNotice(`Đã cập nhật lớp “${updated.name}”.`);
      return updated;
    } catch (reason) {
      setError(readableClassError(reason));
      throw reason;
    } finally {
      setBusyAction(null);
    }
  }

  async function toggleClass(item: ManagedClass) {
    const action = item.is_active ? "tạm dừng" : "mở lại";
    if (!window.confirm(`Bạn có chắc muốn ${action} lớp “${item.name}”?`)) {
      return;
    }
    try {
      await updateClass(item, { is_active: !item.is_active });
    } catch {
      // The shared error alert is populated by updateClass().
    }
  }

  async function rotateJoinCode(item: ManagedClass) {
    if (
      !window.confirm(
        `Đổi mã tham gia của lớp “${item.name}”? Mã cũ sẽ hết hiệu lực ngay.`,
      )
    ) {
      return;
    }
    setBusyAction(`rotate:${item.id}`);
    setError(null);
    setNotice(null);
    try {
      const response = await api.rotateClassJoinCode(item.id);
      replaceClass({
        ...item,
        join_code: response.join_code,
        updated_at: response.updated_at,
      });
      setNotice(`Đã cấp mã tham gia mới cho lớp “${item.name}”.`);
    } catch (reason) {
      setError(readableClassError(reason));
    } finally {
      setBusyAction(null);
    }
  }

  async function copyJoinCode(item: ManagedClass) {
    try {
      await navigator.clipboard.writeText(item.join_code);
      setNotice(`Đã sao chép mã ${item.join_code}.`);
      setError(null);
    } catch {
      setError("Trình duyệt không cho phép sao chép mã tham gia.");
    }
  }

  return (
    <div className="page-stack classroom-page" data-testid="classes-view">
      <section className="section-heading">
        <div>
          <p className="eyebrow blue">Classroom operations</p>
          <h2>Quản lý lớp học</h2>
          <p className="muted">
            {currentUser.role === "teacher"
              ? "Tổ chức lớp, duyệt học viên, giao bài và theo dõi đúng các bài đã nộp."
              : "Theo dõi và kiểm duyệt các lớp học của toàn bộ giáo viên."}
          </p>
        </div>
        <span className="count-badge">{data?.total ?? 0} lớp</span>
      </section>

      {currentUser.role === "teacher" && (
        <section className="panel class-create-panel" data-testid="teacher-class-create">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Lớp mới</p>
              <h3>Tạo không gian học tập</h3>
            </div>
            <span className="panel-chip">Mã tham gia tự động</span>
          </div>
          <form className="management-form class-create-form" onSubmit={createClass}>
            <label>
              <span>Tên lớp</span>
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Ví dụ: English B1 buổi tối"
                maxLength={120}
                required
              />
            </label>
            <label>
              <span>Trình độ mục tiêu</span>
              <select
                value={targetLevel}
                onChange={(event) =>
                  setTargetLevel(event.target.value as "" | CefrLevel)
                }
              >
                <option value="">Chưa xác định</option>
                {LEVELS.map((level) => (
                  <option value={level} key={level}>
                    {level}
                  </option>
                ))}
              </select>
            </label>
            <label className="wide-field">
              <span>Mô tả</span>
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Mục tiêu, lịch học hoặc lưu ý dành cho học viên…"
                maxLength={4000}
                rows={3}
              />
            </label>
            <button
              className="primary-button compact-primary"
              type="submit"
              disabled={busyAction === "create"}
            >
              {busyAction === "create" ? "Đang tạo…" : "Tạo lớp học"}
            </button>
          </form>
        </section>
      )}

      {notice && <div className="inline-alert success-alert">{notice}</div>}
      {error && (
        <div className="inline-alert error-alert" role="alert">
          {error}
        </div>
      )}

      {loading && !data ? (
        <ManagementState label="Đang tải danh sách lớp học…" />
      ) : !data || data.items.length === 0 ? (
        <ManagementEmpty message="Chưa có lớp học nào trong phạm vi quản lý." />
      ) : (
        <section aria-label="Danh sách lớp học đang quản lý">
          <div className="class-grid">
            {data.items.map((item) => (
              <ClassCard
                item={item}
                selected={selectedClass?.id === item.id}
                busyAction={busyAction}
                onSelect={() => setSelectedClass(item)}
                onCopy={() => void copyJoinCode(item)}
                onRotate={() => void rotateJoinCode(item)}
                onToggle={() => void toggleClass(item)}
                key={item.id}
              />
            ))}
          </div>
          <div className="class-pagination-shell">
            <ManagementPagination page={page} total={data.total} onChange={changePage} />
          </div>
        </section>
      )}

      {selectedClass && (
        <ClassWorkspace
          api={api}
          item={selectedClass}
          currentUser={currentUser}
          onClassUpdated={replaceClass}
          onSaveClass={(input) => updateClass(selectedClass, input)}
          onActivity={refreshClasses}
          key={selectedClass.id}
        />
      )}
    </div>
  );
}

function ClassCard({
  item,
  selected,
  busyAction,
  onSelect,
  onCopy,
  onRotate,
  onToggle,
}: {
  item: ManagedClass;
  selected: boolean;
  busyAction: string | null;
  onSelect: () => void;
  onCopy: () => void;
  onRotate: () => void;
  onToggle: () => void;
}) {
  const rotating = busyAction === `rotate:${item.id}`;
  const updating = busyAction === `update:${item.id}`;
  return (
    <article className={`class-card ${selected ? "selected" : ""}`}>
      <header>
        <div>
          <span className={`status-pill ${item.is_active ? "active" : "locked"}`}>
            {item.is_active ? "Đang hoạt động" : "Tạm dừng"}
          </span>
          <h3>{item.name}</h3>
          <p>{item.description || "Chưa có mô tả lớp học."}</p>
        </div>
        <span className="level-mark">{item.target_level ?? "CEFR"}</span>
      </header>

      <div className="class-owner">
        <span className="mini-avatar">
          {item.teacher_display_name.slice(0, 2).toUpperCase()}
        </span>
        <span>
          <strong>{item.teacher_display_name}</strong>
          <small>{item.teacher_email}</small>
        </span>
      </div>

      <div className="class-metrics" aria-label={`Thống kê lớp ${item.name}`}>
        <span>
          <strong>{item.active_member_count}</strong>
          <small>đang học</small>
        </span>
        <span>
          <strong>{item.pending_member_count}</strong>
          <small>chờ duyệt</small>
        </span>
        <span>
          <strong>{item.assignment_count}</strong>
          <small>bài giao</small>
        </span>
      </div>

      <div className="join-code-box">
        <span>
          <small>Mã tham gia</small>
          <code>{item.join_code}</code>
        </span>
        <button type="button" className="row-button" onClick={onCopy}>
          Sao chép
        </button>
        <button
          type="button"
          className="row-button"
          onClick={onRotate}
          disabled={rotating}
        >
          {rotating ? "Đang đổi…" : "Đổi mã"}
        </button>
      </div>

      <footer className="class-card-actions">
        <button
          type="button"
          className="secondary-button"
          onClick={onSelect}
          aria-pressed={selected}
        >
          {selected ? "Đang quản lý" : "Quản lý lớp"}
        </button>
        <button
          type="button"
          className={item.is_active ? "danger-button" : "secondary-button"}
          onClick={onToggle}
          disabled={updating}
        >
          {updating ? "Đang lưu…" : item.is_active ? "Tạm dừng" : "Mở lại"}
        </button>
      </footer>
    </article>
  );
}

function ClassWorkspace({
  api,
  item,
  currentUser,
  onClassUpdated,
  onSaveClass,
  onActivity,
}: {
  api: AdminApi;
  item: ManagedClass;
  currentUser: SessionUser;
  onClassUpdated: (item: ManagedClass) => void;
  onSaveClass: (input: ClassUpdateInput) => Promise<ManagedClass>;
  onActivity: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [members, setMembers] = useState<PageData<ClassMember> | null>(null);
  const [memberPage, setMemberPage] = useState(0);
  const [memberReload, setMemberReload] = useState(0);
  const [memberLoading, setMemberLoading] = useState(true);
  const [memberError, setMemberError] = useState<string | null>(null);
  const [memberNotice, setMemberNotice] = useState<string | null>(null);
  const [busyMemberId, setBusyMemberId] = useState<string | null>(null);
  const [assignments, setAssignments] = useState<PageData<ClassAssignment> | null>(null);
  const [assignmentPage, setAssignmentPage] = useState(0);
  const [assignmentReload, setAssignmentReload] = useState(0);
  const [assignmentLoading, setAssignmentLoading] = useState(true);
  const [assignmentError, setAssignmentError] = useState<string | null>(null);
  const [assignmentNotice, setAssignmentNotice] = useState<string | null>(null);
  const [selectedAssignment, setSelectedAssignment] = useState<ClassAssignment | null>(null);
  const [assignmentBusy, setAssignmentBusy] = useState(false);
  const [assignmentUpdateBusy, setAssignmentUpdateBusy] = useState(false);
  const [assignmentTitle, setAssignmentTitle] = useState("");
  const [instructions, setInstructions] = useState("");
  const [skillType, setSkillType] = useState<AnalysisType>("writing");
  const [assignmentLevel, setAssignmentLevel] = useState<"" | CefrLevel>("");
  const [dueAt, setDueAt] = useState("");

  useEffect(() => {
    let active = true;
    api
      .classMembers(item.id, {
        limit: PAGE_SIZE,
        offset: memberPage * PAGE_SIZE,
      })
      .then((result) => {
        if (!active) return;
        setMembers(result);
        setMemberError(null);
      })
      .catch((reason) => active && setMemberError(readableClassError(reason)))
      .finally(() => active && setMemberLoading(false));
    return () => {
      active = false;
    };
  }, [api, item.id, memberPage, memberReload]);

  useEffect(() => {
    let active = true;
    api
      .classAssignments(item.id, {
        limit: PAGE_SIZE,
        offset: assignmentPage * PAGE_SIZE,
      })
      .then((result) => {
        if (!active) return;
        setAssignments(result);
        setAssignmentError(null);
        setSelectedAssignment((current) => {
          if (!current) return current;
          return result.items.find((assignment) => assignment.id === current.id) ?? current;
        });
      })
      .catch((reason) => active && setAssignmentError(readableClassError(reason)))
      .finally(() => active && setAssignmentLoading(false));
    return () => {
      active = false;
    };
  }, [api, item.id, assignmentPage, assignmentReload]);

  async function updateMember(
    member: ClassMember,
    status: "active" | "removed",
  ) {
    if (
      status === "removed" &&
      !window.confirm(`Xóa ${member.learner_email} khỏi lớp “${item.name}”?`)
    ) {
      return;
    }
    setBusyMemberId(member.id);
    setMemberError(null);
    setMemberNotice(null);
    try {
      await api.updateClassMember(item.id, member.id, status);
      setMemberNotice(
        status === "active"
          ? `Đã duyệt ${member.learner_email} vào lớp.`
          : `Đã đưa ${member.learner_email} ra khỏi lớp.`,
      );
      setMemberLoading(true);
      setMemberReload((value) => value + 1);
      onActivity();
    } catch (reason) {
      setMemberError(readableClassError(reason));
    } finally {
      setBusyMemberId(null);
    }
  }

  async function createAssignment(event: FormEvent) {
    event.preventDefault();
    const input: AssignmentCreateInput = {
      title: assignmentTitle.trim(),
      instructions: instructions.trim(),
      skill_type: skillType,
      target_level: assignmentLevel || null,
      due_at: dueAt ? new Date(dueAt).toISOString() : null,
      status: "published",
    };
    setAssignmentBusy(true);
    setAssignmentError(null);
    setAssignmentNotice(null);
    try {
      const created = await api.createClassAssignment(item.id, input);
      setAssignmentTitle("");
      setInstructions("");
      setSkillType("writing");
      setAssignmentLevel("");
      setDueAt("");
      setAssignmentPage(0);
      setSelectedAssignment(created);
      setAssignmentNotice(`Đã giao bài “${created.title}”.`);
      setAssignmentLoading(true);
      setAssignmentReload((value) => value + 1);
      onActivity();
    } catch (reason) {
      setAssignmentError(readableClassError(reason));
    } finally {
      setAssignmentBusy(false);
    }
  }

  async function updateAssignment(input: AssignmentUpdateInput) {
    if (!selectedAssignment) return;
    setAssignmentUpdateBusy(true);
    setAssignmentError(null);
    setAssignmentNotice(null);
    try {
      const updated = await api.updateClassAssignment(selectedAssignment.id, input);
      setAssignments((current) =>
        current
          ? {
              ...current,
              items: current.items.map((assignment) =>
                assignment.id === updated.id ? updated : assignment,
              ),
            }
          : current,
      );
      setSelectedAssignment(updated);
      setAssignmentNotice(`Đã cập nhật bài “${updated.title}”.`);
      onActivity();
    } catch (reason) {
      setAssignmentError(readableClassError(reason));
    } finally {
      setAssignmentUpdateBusy(false);
    }
  }

  return (
    <section className="class-workspace" data-testid="class-workspace">
      <header className="class-workspace-header">
        <div>
          <p className="eyebrow blue">Đang quản lý</p>
          <h2>{item.name}</h2>
          <p>
            Giáo viên {item.teacher_display_name} · Cập nhật {formatDateTime(item.updated_at)}
          </p>
        </div>
        <div>
          <span className={`status-pill ${item.is_active ? "active" : "locked"}`}>
            {item.is_active ? "Đang hoạt động" : "Tạm dừng"}
          </span>
          <button
            type="button"
            className="secondary-button"
            onClick={() => setEditing((value) => !value)}
            aria-expanded={editing}
          >
            {editing ? "Đóng chỉnh sửa" : "Chỉnh sửa lớp"}
          </button>
        </div>
      </header>

      {editing && (
        <ClassEditForm
          item={item}
          onCancel={() => setEditing(false)}
          onSave={async (input) => {
            const updated = await onSaveClass(input);
            onClassUpdated(updated);
            setEditing(false);
          }}
        />
      )}

      <div className="class-operations-grid">
        <section className="panel roster-panel" aria-labelledby="class-roster-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Roster</p>
              <h3 id="class-roster-title">Học viên trong lớp</h3>
            </div>
            <span className="panel-chip">{members?.total ?? 0} thành viên</span>
          </div>
          {memberNotice && (
            <div className="inline-alert success-alert">{memberNotice}</div>
          )}
          {memberError && (
            <div className="inline-alert error-alert" role="alert">
              {memberError}
            </div>
          )}
          {memberLoading && !members ? (
            <ManagementState label="Đang tải danh sách học viên…" compact />
          ) : !members || members.items.length === 0 ? (
            <ManagementEmpty message="Lớp chưa có yêu cầu tham gia." compact />
          ) : (
            <div className="member-list">
              {members.items.map((member) => (
                <article className="member-row" key={member.id}>
                  <span className="mini-avatar">
                    {member.learner_display_name.slice(0, 2).toUpperCase()}
                  </span>
                  <span className="member-copy">
                    <strong>{member.learner_display_name}</strong>
                    <small>{member.learner_email}</small>
                    <small>
                      {member.learner_level ?? "Chưa đặt trình độ"} · Tài khoản {member.learner_is_active ? "hoạt động" : "đã khóa"}
                    </small>
                  </span>
                  <span className={`member-status ${member.status}`}>
                    {membershipLabel(member.status)}
                  </span>
                  <span className="member-actions">
                    {member.status === "pending" && (
                      <button
                        type="button"
                        className="row-button approve-button"
                        disabled={busyMemberId === member.id}
                        onClick={() => void updateMember(member, "active")}
                      >
                        Duyệt
                      </button>
                    )}
                    {member.status !== "removed" && (
                      <button
                        type="button"
                        className="row-button"
                        disabled={busyMemberId === member.id}
                        onClick={() => void updateMember(member, "removed")}
                      >
                        {busyMemberId === member.id ? "Đang lưu…" : "Xóa"}
                      </button>
                    )}
                  </span>
                </article>
              ))}
              <ManagementPagination
                page={memberPage}
                total={members.total}
                onChange={(nextPage) => {
                  setMemberLoading(true);
                  setMemberPage(nextPage);
                }}
              />
            </div>
          )}
        </section>

        <section className="panel assignments-panel" aria-labelledby="assignments-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Assignments</p>
              <h3 id="assignments-title">Giao bài cho lớp</h3>
            </div>
            <span className="panel-chip">{assignments?.total ?? 0} bài</span>
          </div>

          <form className="management-form assignment-form" onSubmit={createAssignment}>
            <label>
              <span>Tiêu đề bài tập</span>
              <input
                value={assignmentTitle}
                onChange={(event) => setAssignmentTitle(event.target.value)}
                maxLength={160}
                required
              />
            </label>
            <label>
              <span>Kỹ năng</span>
              <select
                value={skillType}
                onChange={(event) => setSkillType(event.target.value as AnalysisType)}
              >
                {SKILLS.map((skill) => (
                  <option value={skill} key={skill}>
                    {skillLabel(skill)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Trình độ gợi ý</span>
              <select
                value={assignmentLevel}
                onChange={(event) =>
                  setAssignmentLevel(event.target.value as "" | CefrLevel)
                }
              >
                <option value="">Không giới hạn</option>
                {LEVELS.map((level) => (
                  <option value={level} key={level}>
                    {level}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Hạn nộp (không bắt buộc)</span>
              <input
                type="datetime-local"
                value={dueAt}
                onChange={(event) => setDueAt(event.target.value)}
              />
            </label>
            <label className="wide-field">
              <span>Hướng dẫn</span>
              <textarea
                value={instructions}
                onChange={(event) => setInstructions(event.target.value)}
                maxLength={10000}
                rows={3}
                required
              />
            </label>
            <button
              className="primary-button compact-primary"
              type="submit"
              disabled={assignmentBusy || !item.is_active}
              title={!item.is_active ? "Mở lại lớp trước khi giao bài" : undefined}
            >
              {assignmentBusy ? "Đang giao…" : "Giao bài"}
            </button>
          </form>

          {assignmentNotice && (
            <div className="inline-alert success-alert">{assignmentNotice}</div>
          )}
          {assignmentError && (
            <div className="inline-alert error-alert" role="alert">
              {assignmentError}
            </div>
          )}
          {assignmentLoading && !assignments ? (
            <ManagementState label="Đang tải bài tập…" compact />
          ) : !assignments || assignments.items.length === 0 ? (
            <ManagementEmpty message="Lớp chưa có bài tập nào." compact />
          ) : (
            <div className="assignment-list">
              {assignments.items.map((assignment) => (
                <button
                  type="button"
                  className={selectedAssignment?.id === assignment.id ? "active" : ""}
                  onClick={() => setSelectedAssignment(assignment)}
                  aria-pressed={selectedAssignment?.id === assignment.id}
                  key={assignment.id}
                >
                  <span className={`type-badge ${assignment.skill_type}`}>
                    {skillLabel(assignment.skill_type)}
                  </span>
                  <span>
                    <strong>{assignment.title}</strong>
                    <small>
                      {assignmentStatusLabel(assignment)} · Hạn {formatDateTime(assignment.due_at)}
                    </small>
                    <small>
                      {assignment.submission_count} bài nộp · giao bởi {assignment.created_by_display_name}
                    </small>
                  </span>
                </button>
              ))}
              <ManagementPagination
                page={assignmentPage}
                total={assignments.total}
                onChange={(nextPage) => {
                  setAssignmentLoading(true);
                  setAssignmentPage(nextPage);
                }}
              />
            </div>
          )}
        </section>
      </div>

      {selectedAssignment && (
        <div className="assignment-detail-stack">
          <AssignmentControls
            assignment={selectedAssignment}
            busy={assignmentUpdateBusy}
            key={`${selectedAssignment.id}:${selectedAssignment.due_at ?? ""}`}
            onUpdate={updateAssignment}
          />
          <SubmissionsPanel
            api={api}
            assignment={selectedAssignment}
            viewerRole={currentUser.role}
            key={selectedAssignment.id}
          />
        </div>
      )}
    </section>
  );
}

function AssignmentControls({
  assignment,
  busy,
  onUpdate,
}: {
  assignment: ClassAssignment;
  busy: boolean;
  onUpdate: (input: AssignmentUpdateInput) => Promise<void>;
}) {
  const [editableDueAt, setEditableDueAt] = useState(toDateTimeLocal(assignment.due_at));

  function saveDueAt(event: FormEvent) {
    event.preventDefault();
    void onUpdate({
      due_at: editableDueAt ? new Date(editableDueAt).toISOString() : null,
    });
  }

  function toggleStatus() {
    const nextStatus = assignment.status === "published" ? "closed" : "published";
    if (
      nextStatus === "closed" &&
      !window.confirm(`Đóng bài “${assignment.title}” và ngừng nhận bài nộp mới?`)
    ) {
      return;
    }
    void onUpdate({ status: nextStatus });
  }

  return (
    <section className="panel assignment-controls" aria-labelledby="assignment-controls-title">
      <div>
        <p className="eyebrow">Assignment lifecycle</p>
        <h3 id="assignment-controls-title">Điều hành bài · {assignment.title}</h3>
        <p>
          Trạng thái <strong>{assignmentStatusLabel(assignment)}</strong> · Hạn hiện tại {formatDateTime(assignment.due_at)}
        </p>
      </div>
      <form className="assignment-due-form" onSubmit={saveDueAt}>
        <label>
          <span>Gia hạn hoặc bỏ hạn nộp</span>
          <input
            type="datetime-local"
            value={editableDueAt}
            onChange={(event) => setEditableDueAt(event.target.value)}
          />
        </label>
        <button className="secondary-button" type="submit" disabled={busy}>
          {busy ? "Đang lưu…" : "Lưu hạn nộp"}
        </button>
      </form>
      <button
        className={assignment.status === "published" ? "danger-button" : "primary-button"}
        type="button"
        disabled={busy}
        onClick={toggleStatus}
      >
        {assignment.status === "published" ? "Đóng bài tập" : "Mở lại bài tập"}
      </button>
    </section>
  );
}

function ClassEditForm({
  item,
  onSave,
  onCancel,
}: {
  item: ManagedClass;
  onSave: (input: ClassUpdateInput) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState(item.name);
  const [description, setDescription] = useState(item.description ?? "");
  const [targetLevel, setTargetLevel] = useState<"" | CefrLevel>(
    item.target_level ?? "",
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onSave({
        name: name.trim(),
        description: description.trim(),
        target_level: targetLevel || null,
      });
    } catch (reason) {
      setError(readableClassError(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel management-form class-edit-form" onSubmit={submit}>
      <label>
        <span>Tên lớp</span>
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          maxLength={120}
          required
        />
      </label>
      <label>
        <span>Trình độ mục tiêu</span>
        <select
          value={targetLevel}
          onChange={(event) =>
            setTargetLevel(event.target.value as "" | CefrLevel)
          }
        >
          <option value="">Chưa xác định</option>
          {LEVELS.map((level) => (
            <option value={level} key={level}>
              {level}
            </option>
          ))}
        </select>
      </label>
      <label className="wide-field">
        <span>Mô tả</span>
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          maxLength={4000}
          rows={3}
        />
      </label>
      {error && (
        <div className="inline-alert error-alert wide-field" role="alert">
          {error}
        </div>
      )}
      <div className="form-actions wide-field">
        <button type="button" className="secondary-button" onClick={onCancel}>
          Hủy
        </button>
        <button type="submit" className="primary-button compact-primary" disabled={busy}>
          {busy ? "Đang lưu…" : "Lưu thay đổi"}
        </button>
      </div>
    </form>
  );
}

function SubmissionsPanel({
  api,
  assignment,
  viewerRole,
}: {
  api: AdminApi;
  assignment: ClassAssignment;
  viewerRole: SessionUser["role"];
}) {
  const [data, setData] = useState<PageData<AssignmentSubmission> | null>(null);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api
      .assignmentSubmissions(assignment.id, {
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      })
      .then((result) => {
        if (!active) return;
        setData(result);
        setError(null);
      })
      .catch((reason) => active && setError(readableClassError(reason)))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [api, assignment.id, page]);

  return (
    <section className="panel submissions-panel" data-testid="assignment-submissions">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Submitted analyses</p>
          <h3>Bài đã nộp · {assignment.title}</h3>
          <p className="submission-privacy-note">
            {viewerRole === "teacher" ? "Giáo viên" : "Quản trị viên"} chỉ xem nội dung phân tích được học viên chủ động nộp cho bài này.
          </p>
        </div>
        <span className="panel-chip">{data?.total ?? 0} bài nộp</span>
      </div>
      {error && (
        <div className="inline-alert error-alert" role="alert">
          {error}
        </div>
      )}
      {loading && !data ? (
        <ManagementState label="Đang tải bài đã nộp…" compact />
      ) : !data || data.items.length === 0 ? (
        <ManagementEmpty message="Chưa có học viên nộp bài." compact />
      ) : (
        <div className="submission-list">
          {data.items.map((submission) => (
            <article className="submission-card" key={submission.id}>
              <header>
                <span className="mini-avatar">
                  {submission.learner_display_name.slice(0, 2).toUpperCase()}
                </span>
                <span>
                  <strong>{submission.learner_display_name}</strong>
                  <small>{submission.learner_email}</small>
                </span>
                <span className="submission-meta">
                  Lần {submission.attempt_number} · {formatDateTime(submission.submitted_at)}
                </span>
              </header>
              <div className="submission-summary">
                <span className={`type-badge ${submission.analysis.type}`}>
                  {skillLabel(submission.analysis.type)}
                </span>
                <span>Provider {submission.analysis.provider}</span>
                <strong>
                  {submission.analysis.score === null
                    ? "Không điểm"
                    : `${submission.analysis.score}/10`}
                </strong>
              </div>
              <p>{submission.analysis.input_text}</p>
              <details>
                <summary>Xem kết quả phân tích đã nộp</summary>
                <pre>{JSON.stringify(submission.analysis.result, null, 2)}</pre>
              </details>
            </article>
          ))}
          <ManagementPagination
            page={page}
            total={data.total}
            onChange={(nextPage) => {
              setLoading(true);
              setPage(nextPage);
            }}
          />
        </div>
      )}
    </section>
  );
}

function ManagementState({
  label,
  compact = false,
}: {
  label: string;
  compact?: boolean;
}) {
  return (
    <div className={`state-card loading-state ${compact ? "compact-state" : ""}`} role="status">
      <span className="loading-pulse" />
      <strong>{label}</strong>
    </div>
  );
}

function ManagementEmpty({
  message,
  compact = false,
}: {
  message: string;
  compact?: boolean;
}) {
  return (
    <div className={`state-card empty-state ${compact ? "compact-state" : ""}`}>
      <span className="empty-mark">LM</span>
      <strong>{message}</strong>
    </div>
  );
}
