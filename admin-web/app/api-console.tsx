"use client";

import { FormEvent, KeyboardEvent, useMemo, useState } from "react";
import {
  ApiConsoleMethod,
  ApiConsoleRequest,
  ApiConsoleResponse,
  AdminApi,
} from "./lib/api";
import {
  API_PRESETS,
  buildCurl,
  formatBytes,
  parseHeaderJson,
} from "./lib/api-console";

type HistoryItem = {
  id: string;
  method: ApiConsoleMethod;
  path: string;
  status: number;
  durationMs: number;
  createdAt: string;
};

const HISTORY_KEY = "learnmate_api_console_history";
const METHODS: ApiConsoleMethod[] = ["GET", "POST", "PATCH", "DELETE"];

function readHistory(): HistoryItem[] {
  if (typeof window === "undefined") return [];
  try {
    const value = JSON.parse(sessionStorage.getItem(HISTORY_KEY) ?? "[]");
    return Array.isArray(value) ? value.slice(0, 12) : [];
  } catch {
    return [];
  }
}

function prettyBody(response: ApiConsoleResponse) {
  if (typeof response.body === "string") return response.body || "(empty response)";
  return JSON.stringify(response.body, null, 2);
}

export function ApiConsole({ api, baseUrl }: { api: AdminApi; baseUrl: string }) {
  const [method, setMethod] = useState<ApiConsoleMethod>("GET");
  const [path, setPath] = useState("/health/ready");
  const [headersText, setHeadersText] = useState("{}");
  const [body, setBody] = useState("");
  const [response, setResponse] = useState<ApiConsoleResponse | null>(null);
  const [responseTab, setResponseTab] = useState<"body" | "headers">("body");
  const [history, setHistory] = useState<HistoryItem[]>(readHistory);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [copied, setCopied] = useState(false);

  const request = useMemo<ApiConsoleRequest>(() => {
    let headers: Record<string, string> = {};
    try {
      headers = parseHeaderJson(headersText);
    } catch {
      // Validation is reported when sending; cURL preview can omit invalid headers.
    }
    return { method, path, headers, body };
  }, [body, headersText, method, path]);

  function selectPreset(index: number) {
    const preset = API_PRESETS[index];
    setMethod(preset.method);
    setPath(preset.path);
    setBody(preset.body ?? "");
    setHeadersText("{}");
    setResponse(null);
    setError(null);
  }

  async function send(event?: FormEvent) {
    event?.preventDefault();
    setRunning(true);
    setError(null);
    setCopied(false);
    try {
      const headers = parseHeaderJson(headersText);
      const nextResponse = await api.consoleRequest({ method, path, headers, body });
      setResponse(nextResponse);
      setResponseTab("body");
      const nextHistory = [
        {
          id: crypto.randomUUID(),
          method,
          path,
          status: nextResponse.status,
          durationMs: nextResponse.durationMs,
          createdAt: new Date().toISOString(),
        },
        ...history,
      ].slice(0, 12);
      setHistory(nextHistory);
      sessionStorage.setItem(HISTORY_KEY, JSON.stringify(nextHistory));
    } catch (reason) {
      setResponse(null);
      setError(reason instanceof Error ? reason.message : "Không thể gửi request.");
    } finally {
      setRunning(false);
    }
  }

  function handleShortcut(event: KeyboardEvent<HTMLFormElement>) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      void send();
    }
  }

  async function copyCurl() {
    try {
      await navigator.clipboard.writeText(buildCurl(baseUrl, request));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setError("Trình duyệt không cho phép ghi vào clipboard.");
    }
  }

  return (
    <div className="page-stack api-console-page">
      <section className="section-heading console-heading">
        <div>
          <p className="eyebrow blue">Backend workbench</p>
          <h2>API Console</h2>
          <p className="muted">Gửi request thật, đọc response và tái hiện bằng cURL.</p>
        </div>
        <div className="console-heading-actions">
          <span className="auth-chip">JWT admin tự động</span>
          <a className="secondary-button docs-link" href={`${baseUrl}/docs`} target="_blank" rel="noreferrer">Mở Swagger</a>
        </div>
      </section>

      <section className="console-environment">
        <span className="status-dot" />
        <span>Environment</span>
        <code>{baseUrl}</code>
        <small>Request bị giới hạn trong origin backend này.</small>
      </section>

      <section className="console-layout">
        <aside className="preset-panel">
          <div className="panel-heading"><div><p className="eyebrow">Collection</p><h3>LearnMate API</h3></div></div>
          <div className="preset-list">
            {API_PRESETS.map((preset, index) => (
              <button type="button" key={`${preset.method}-${preset.path}`} onClick={() => selectPreset(index)}>
                <span className={`method-label ${preset.method.toLowerCase()}`}>{preset.method}</span>
                <span><strong>{preset.name}</strong><small>{preset.description}</small></span>
              </button>
            ))}
          </div>
          <div className="history-heading"><strong>Lịch sử phiên</strong><small>Không lưu body hoặc token</small></div>
          <div className="history-list">
            {history.length === 0 ? <p>Chưa có request.</p> : history.map((item) => (
              <button type="button" key={item.id} onClick={() => { setMethod(item.method); setPath(item.path); }}>
                <span className={`history-status ${item.status >= 400 ? "bad" : "good"}`}>{item.status}</span>
                <span><strong>{item.method} {item.path}</strong><small>{item.durationMs} ms</small></span>
              </button>
            ))}
          </div>
        </aside>

        <div className="console-workspace">
          <form className="request-builder" onSubmit={send} onKeyDown={handleShortcut}>
            <div className="request-line">
              <select aria-label="HTTP method" value={method} className={`method-select ${method.toLowerCase()}`} onChange={(event) => setMethod(event.target.value as ApiConsoleMethod)}>
                {METHODS.map((item) => <option value={item} key={item}>{item}</option>)}
              </select>
              <label className="request-url"><span>{baseUrl}</span><input aria-label="API path" value={path} onChange={(event) => setPath(event.target.value)} required /></label>
              <button className="send-button" type="submit" disabled={running}>{running ? "Đang gửi…" : "Gửi"}</button>
            </div>

            <div className="request-fields">
              <label><span>Headers <small>JSON object</small></span><textarea value={headersText} onChange={(event) => setHeadersText(event.target.value)} spellCheck={false} /></label>
              <label><span>Body <small>{method === "GET" ? "GET không gửi body" : "raw JSON"}</small></span><textarea value={body} onChange={(event) => setBody(event.target.value)} disabled={method === "GET"} placeholder={method === "GET" ? "Không áp dụng" : '{\n  "key": "value"\n}'} spellCheck={false} /></label>
            </div>
            <div className="request-footer"><span><kbd>Ctrl</kbd> + <kbd>Enter</kbd> để gửi</span><button className="text-button" type="button" onClick={() => void copyCurl()}>{copied ? "Đã sao chép" : "Sao chép cURL"}</button></div>
          </form>

          <section className="response-panel" aria-live="polite">
            <header>
              <div><p className="eyebrow">Response</p><h3>{response ? `${response.status} ${response.statusText}` : "Chưa có phản hồi"}</h3></div>
              {response && <div className="response-metrics"><span className={response.ok ? "success" : "failure"}>{response.ok ? "Thành công" : "Có lỗi"}</span><span>{response.durationMs} ms</span><span>{formatBytes(response.sizeBytes)}</span></div>}
            </header>
            {error ? <div className="console-error" role="alert"><strong>Request chưa được gửi</strong><span>{error}</span></div> : !response ? <div className="response-empty"><span>HTTP</span><p>Chọn một preset hoặc nhập endpoint rồi nhấn Gửi.</p></div> : (
              <>
                <div className="response-tabs">
                  <button type="button" className={responseTab === "body" ? "active" : ""} onClick={() => setResponseTab("body")}>Body</button>
                  <button type="button" className={responseTab === "headers" ? "active" : ""} onClick={() => setResponseTab("headers")}>Headers ({Object.keys(response.headers).length})</button>
                </div>
                <pre className="response-code">{responseTab === "body" ? prettyBody(response) : JSON.stringify(response.headers, null, 2)}</pre>
              </>
            )}
          </section>
        </div>
      </section>
    </div>
  );
}
