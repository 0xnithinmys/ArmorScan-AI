"use client";

import { FormEvent, useCallback, useEffect, useState, useTransition } from "react";
import type { ReactNode } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000/api/v1";

type ApiError = { detail?: string };
type User = {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
};
type Target = {
  id: string;
  name: string;
  target_type: "url" | "github" | "api" | string;
  target_url: string;
  scope: string[];
  authorization_status: string;
  authorization_proof_type: string | null;
  created_at: string;
};
type Scan = {
  id: string;
  target_id: string;
  requested_by_id: string;
  scan_type: string;
  status: string;
  scope: string[];
  celery_task_id: string | null;
  summary: string | null;
  agent_trace: Array<Record<string, unknown>>;
  report_json: Record<string, unknown> | null;
  armoriq_token: string | null;
  intent_plan: Record<string, unknown> | null;
  policy_decisions: Array<Record<string, unknown>>;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};
type Finding = {
  id: string;
  scan_id: string;
  severity: string;
  title: string;
  location: string;
  confidence: number;
  risk_score: number;
  risk_rating: string;
  status: string;
  summary: string;
  business_impact: string | null;
  remediation: string | null;
  risk_factors: Record<string, unknown>;
  reproduction_steps: string[];
  created_at: string;
};
type AuditEvent = {
  id: string;
  user_id: string | null;
  target_id: string | null;
  scan_id: string | null;
  event_type: string;
  message: string;
  details: Record<string, unknown> | null;
  created_at: string;
};

type ScanCreateResponse = { scan: Scan; target: Target };

const emptyTargetForm = {
  name: "",
  target_type: "url",
  target_url: "",
  scope: "",
  authorization_attestation: true,
};

const emptyScanForm = {
  target_id: "",
  target_name: "",
  target_url: "",
  scan_type: "url",
  scope: "",
  authorization_attestation: true,
};

function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` };
}

function splitScope(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

async function readError(response: Response) {
  try {
    const body = (await response.json()) as ApiError;
    return body.detail || `${response.status} ${response.statusText}`;
  } catch {
    return `${response.status} ${response.statusText}`;
  }
}

function severityStyle(value: string) {
  switch (value.toLowerCase()) {
    case "critical":
      return "border-[#ff7c70]/40 bg-[#5f1919] text-[#ffb3ad]";
    case "high":
      return "border-[#ffb15f]/40 bg-[#5e3512] text-[#ffd8ad]";
    case "medium":
      return "border-[#e2eb72]/40 bg-[#3f4216] text-[#eef5a3]";
    case "low":
      return "border-[#8bd8ff]/35 bg-[#16364a] text-[#b9e7ff]";
    default:
      return "border-white/10 bg-white/8 text-white/70";
  }
}

function statusStyle(value: string) {
  switch (value.toLowerCase()) {
    case "completed":
    case "verified":
      return "text-[#9ef3cf]";
    case "queued":
    case "planning":
    case "executing":
    case "observing":
    case "reflecting":
      return "text-[#ffd38f]";
    case "failed":
    case "cancelled":
    case "pending":
      return "text-[#ffaaa4]";
    default:
      return "text-white/60";
  }
}

function shortId(value: string) {
  return value.slice(0, 8);
}

export default function Home() {
  const [token, setToken] = useState(() =>
    typeof window === "undefined" ? "" : window.localStorage.getItem("armorscan_token") || "",
  );
  const [user, setUser] = useState<User | null>(null);
  const [targets, setTargets] = useState<Target[]>([]);
  const [scans, setScans] = useState<Scan[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [streamEvents, setStreamEvents] = useState<string[]>([]);
  const [selectedScanId, setSelectedScanId] = useState("");
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authForm, setAuthForm] = useState({
    email: "",
    password: "",
    full_name: "",
  });
  const [targetForm, setTargetForm] = useState(emptyTargetForm);
  const [scanForm, setScanForm] = useState(emptyScanForm);
  const [message, setMessage] = useState("Connect to the backend to load live ArmorScan data.");
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        ...(token ? authHeaders(token) : {}),
        ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...options.headers,
      },
    });
    if (!response.ok) {
      throw new Error(await readError(response));
    }
    if (response.status === 204) {
      return undefined as T;
    }
    return (await response.json()) as T;
  }

  const refreshData = useCallback(async (activeToken = token) => {
    if (!activeToken) return;
    setError("");
    const request = async <T,>(path: string) => {
      const response = await fetch(`${API_BASE}${path}`, {
        headers: authHeaders(activeToken),
      });
      if (!response.ok) {
        throw new Error(await readError(response));
      }
      return (await response.json()) as T;
    };

    const [me, nextTargets, nextScans, nextFindings, nextAuditEvents] = await Promise.all([
      request<User>("/auth/me"),
      request<Target[]>("/targets/"),
      request<Scan[]>("/scans/"),
      request<Finding[]>("/findings/"),
      request<AuditEvent[]>("/audit/?limit=75"),
    ]);
    setUser(me);
    setTargets(nextTargets);
    setScans(nextScans);
    setFindings(nextFindings);
    setAuditEvents(nextAuditEvents);
    setSelectedScanId((current) => current || nextScans[0]?.id || "");
    setMessage(`Live backend sync complete for ${me.email}.`);
  }, [token]);

  useEffect(() => {
    if (!token) return;
    startTransition(() => {
      refreshData(token).catch((err: Error) => {
        setError(err.message);
        window.localStorage.removeItem("armorscan_token");
        setToken("");
      });
    });
  }, [refreshData, token]);

  useEffect(() => {
    if (!selectedScanId || !token) return;
    const wsBase = API_BASE.replace(/^http/, "ws");
    const socket = new WebSocket(
      `${wsBase}/ws/scans/${selectedScanId}/stream?token=${encodeURIComponent(token)}`,
    );
    socket.onmessage = (event) => {
      setStreamEvents((current) => [event.data, ...current].slice(0, 8));
    };
    socket.onerror = () => {
      setStreamEvents((current) => ["WebSocket stream unavailable; backend will fall back to polling when connected.", ...current].slice(0, 8));
    };
    return () => socket.close();
  }, [selectedScanId, token]);

  async function handleAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      if (authMode === "register") {
        await fetch(`${API_BASE}/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(authForm),
        }).then(async (response) => {
          if (!response.ok) throw new Error(await readError(response));
        });
      }

      const formData = new FormData();
      formData.set("username", authForm.email);
      formData.set("password", authForm.password);
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) throw new Error(await readError(response));
      const body = (await response.json()) as { access_token: string };
      window.localStorage.setItem("armorscan_token", body.access_token);
      setToken(body.access_token);
      await refreshData(body.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    }
  }

  async function createTarget(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      await api<Target>("/targets/", {
        method: "POST",
        body: JSON.stringify({
          ...targetForm,
          scope: splitScope(targetForm.scope),
        }),
      });
      setTargetForm(emptyTargetForm);
      await refreshData();
      setMessage("Target created and synced from backend.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Target creation failed");
    }
  }

  async function authorizeTarget(targetId: string) {
    setError("");
    try {
      await api<Target>(`/targets/${targetId}/authorize`, {
        method: "POST",
        body: JSON.stringify({
          proof_type: "manual_attestation",
          proof: "I_AM_AUTHORIZED",
        }),
      });
      await refreshData();
      setMessage("Target authorization verified with backend policy.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authorization failed");
    }
  }

  async function deleteTarget(targetId: string) {
    setError("");
    try {
      await api<void>(`/targets/${targetId}`, { method: "DELETE" });
      await refreshData();
      setMessage("Target deleted.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  async function createScan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      const payload =
        scanForm.target_id === "__new__"
          ? {
              target_name: scanForm.target_name,
              target_url: scanForm.target_url,
              scan_type: scanForm.scan_type,
              scope: splitScope(scanForm.scope),
              authorization_attestation: scanForm.authorization_attestation,
            }
          : {
              target_id: scanForm.target_id,
              scan_type: scanForm.scan_type,
              scope: splitScope(scanForm.scope),
              authorization_attestation: scanForm.authorization_attestation,
            };
      const response = await api<ScanCreateResponse>("/scans/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setSelectedScanId(response.scan.id);
      setScanForm(emptyScanForm);
      await refreshData();
      setMessage("Scan queued. If Redis/Celery is online, the worker will pick it up.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan creation failed");
    }
  }

  async function updateFindingStatus(findingId: string, status: string) {
    setError("");
    try {
      await api<Finding>(`/findings/${findingId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      await refreshData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Finding update failed");
    }
  }

  async function cancelScan(scanId: string) {
    setError("");
    try {
      await api<Scan>(`/scans/${scanId}/cancel`, { method: "POST" });
      await refreshData();
      setMessage("Scan cancelled.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cancel failed");
    }
  }

  async function downloadReport(kind: "json" | "sarif" | "pdf" | "markdown") {
    if (!selectedScanId) return;
    setError("");
    try {
      const response = await fetch(`${API_BASE}/reports/${selectedScanId}/${kind}`, {
        headers: authHeaders(token),
      });
      if (!response.ok) throw new Error(await readError(response));
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `armorscan-${selectedScanId}.${kind === "markdown" ? "md" : kind}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Report download failed");
    }
  }

  const selectedScan = scans.find((scan) => scan.id === selectedScanId) ?? scans[0];
  const selectedTarget = selectedScan
    ? targets.find((target) => target.id === selectedScan.target_id)
    : targets[0];
  const selectedReport = selectedScan?.report_json?.risk_report as
    | { executive_summary?: { overall_risk_score?: number; overall_risk_rating?: string } }
    | undefined;
  const activeFindings = selectedScan
    ? findings.filter((finding) => finding.scan_id === selectedScan.id)
    : findings;
  const liveStatuses = new Set(["queued", "planning", "executing", "observing", "reflecting"]);
  const metrics = [
    { label: "Targets", value: targets.length, detail: `${targets.filter((t) => t.authorization_status === "verified").length} verified` },
    { label: "Scans", value: scans.length, detail: `${scans.filter((scan) => liveStatuses.has(scan.status)).length} active` },
    { label: "Findings", value: findings.length, detail: `${findings.filter((finding) => finding.risk_rating === "critical").length} critical` },
    { label: "Policy events", value: auditEvents.filter((event) => event.event_type.startsWith("policy.")).length, detail: "ArmorIQ enforced" },
  ];

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_12%_8%,rgba(215,242,102,0.2),transparent_24%),radial-gradient(circle_at_84%_0%,rgba(90,179,255,0.18),transparent_26%),linear-gradient(180deg,#07111f_0%,#0a1321_48%,#070d16_100%)] text-[#f7f4ea]">
      <div className="mx-auto grid min-h-screen max-w-[1800px] gap-5 px-4 py-4 lg:grid-cols-[280px_1fr]">
        <aside className="rounded-[30px] border border-white/10 bg-[#07111c]/82 p-5 shadow-[0_24px_90px_rgba(0,0,0,0.4)] backdrop-blur">
          <p className="text-xs uppercase tracking-[0.42em] text-[#d7f266]">ArmorScan AI</p>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight text-white">Backend-mapped cockpit</h1>
          <p className="mt-3 text-sm leading-6 text-white/62">
            Auth, targets, scans, findings, policy events, risk reports, and exports are wired to the FastAPI surface.
          </p>

          <div className="mt-6 rounded-[24px] border border-white/10 bg-white/6 p-4">
            <p className="text-xs uppercase tracking-[0.26em] text-white/42">API base</p>
            <p className="mt-2 break-all font-mono text-xs text-[#9ef3cf]">{API_BASE}</p>
          </div>

          <nav className="mt-6 grid gap-2 text-sm">
            {["Auth", "Targets", "Scans", "Findings", "Reports", "Audit", "Policy", "Stream"].map((item) => (
              <a
                key={item}
                href={`#${item.toLowerCase()}`}
                className="rounded-2xl border border-white/8 bg-white/5 px-4 py-3 text-white/72 transition hover:bg-[#d7f266] hover:text-[#102018]"
              >
                {item}
              </a>
            ))}
          </nav>

          <button
            className="mt-6 w-full rounded-2xl border border-white/10 bg-white/6 px-4 py-3 text-sm text-white/70 transition hover:bg-white/10"
            onClick={() => {
              window.localStorage.removeItem("armorscan_token");
              setToken("");
              setUser(null);
              setTargets([]);
                setScans([]);
                setFindings([]);
                setAuditEvents([]);
                setStreamEvents([]);
              }}
          >
            Sign out / clear token
          </button>
        </aside>

        <section className="space-y-5">
          <header className="rounded-[34px] border border-white/10 bg-[#08101b]/82 p-5 shadow-[0_24px_80px_rgba(0,0,0,0.35)] backdrop-blur sm:p-7">
            <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.4em] text-[#8db39d]">Frontend alignment pass</p>
                <h2 className="mt-3 max-w-4xl text-4xl font-semibold tracking-tight text-white sm:text-6xl">
                  A real control plane for the backend we built.
                </h2>
                <p className="mt-4 max-w-3xl text-sm leading-7 text-white/68">
                  No static dummy queue here: every card below is driven by FastAPI endpoints, with graceful empty states when the backend has no data yet.
                </p>
              </div>
              <button
                disabled={!token || isPending}
                onClick={() =>
                  startTransition(() => {
                    refreshData().catch((err: Error) => setError(err.message));
                  })
                }
                className="rounded-full bg-[#d7f266] px-6 py-3 text-sm font-semibold text-[#122111] transition hover:bg-[#e9fb8e] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isPending ? "Syncing..." : "Refresh backend"}
              </button>
            </div>

            {(message || error) && (
              <div className="mt-5 grid gap-3 lg:grid-cols-2">
                {message && <p className="rounded-2xl border border-[#d7f266]/20 bg-[#d7f266]/10 px-4 py-3 text-sm text-[#efffba]">{message}</p>}
                {error && <p className="rounded-2xl border border-[#ff7c70]/30 bg-[#5f1919]/40 px-4 py-3 text-sm text-[#ffb3ad]">{error}</p>}
              </div>
            )}
          </header>

          <section id="auth" className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
            <form onSubmit={handleAuth} className="rounded-[30px] border border-white/10 bg-white/6 p-5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-[#8db39d]">Auth</p>
                  <h3 className="mt-2 text-2xl font-semibold text-white">{user ? user.full_name : "Login or register"}</h3>
                </div>
                <div className="rounded-full border border-white/10 p-1 text-xs">
                  {(["login", "register"] as const).map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => setAuthMode(mode)}
                      className={`rounded-full px-3 py-2 capitalize ${authMode === mode ? "bg-[#d7f266] text-[#102018]" : "text-white/62"}`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-5 grid gap-3">
                {authMode === "register" && (
                  <input
                    className="rounded-2xl border border-white/10 bg-[#07111c] px-4 py-3 text-sm outline-none focus:border-[#d7f266]"
                    placeholder="Full name"
                    value={authForm.full_name}
                    onChange={(event) => setAuthForm({ ...authForm, full_name: event.target.value })}
                  />
                )}
                <input
                  className="rounded-2xl border border-white/10 bg-[#07111c] px-4 py-3 text-sm outline-none focus:border-[#d7f266]"
                  placeholder="Email"
                  type="email"
                  value={authForm.email}
                  onChange={(event) => setAuthForm({ ...authForm, email: event.target.value })}
                />
                <input
                  className="rounded-2xl border border-white/10 bg-[#07111c] px-4 py-3 text-sm outline-none focus:border-[#d7f266]"
                  placeholder="Password"
                  type="password"
                  value={authForm.password}
                  onChange={(event) => setAuthForm({ ...authForm, password: event.target.value })}
                />
                <button className="rounded-2xl bg-[#d7f266] px-4 py-3 text-sm font-semibold text-[#102018]">
                  {authMode === "register" ? "Register and login" : "Login"}
                </button>
              </div>
            </form>

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {metrics.map((metric) => (
                <div key={metric.label} className="rounded-[28px] border border-white/10 bg-white/6 p-5">
                  <p className="text-sm text-white/58">{metric.label}</p>
                  <p className="mt-3 text-4xl font-semibold text-white">{metric.value}</p>
                  <p className="mt-2 text-sm text-[#9ec9a8]">{metric.detail}</p>
                </div>
              ))}
            </div>
          </section>

          <section id="targets" className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
            <form onSubmit={createTarget} className="rounded-[30px] border border-white/10 bg-[linear-gradient(145deg,rgba(215,242,102,0.13),rgba(255,255,255,0.035))] p-5">
              <p className="text-xs uppercase tracking-[0.3em] text-[#d7f266]">Targets API</p>
              <h3 className="mt-2 text-2xl font-semibold text-white">Create target</h3>
              <div className="mt-5 grid gap-3 md:grid-cols-2">
                <input className="field" placeholder="Target name (optional)" value={targetForm.name} onChange={(e) => setTargetForm({ ...targetForm, name: e.target.value })} />
                <select className="field" value={targetForm.target_type} onChange={(e) => setTargetForm({ ...targetForm, target_type: e.target.value })}>
                  <option value="url">URL</option>
                  <option value="api">API</option>
                  <option value="github">GitHub/local repo</option>
                </select>
                <input className="field md:col-span-2" placeholder="https://example.com or C:\\path\\repo" value={targetForm.target_url} onChange={(e) => setTargetForm({ ...targetForm, target_url: e.target.value })} />
                <input className="field md:col-span-2" placeholder="Scope hosts, comma-separated" value={targetForm.scope} onChange={(e) => setTargetForm({ ...targetForm, scope: e.target.value })} />
                <label className="md:col-span-2 flex items-center gap-3 rounded-2xl border border-white/10 bg-[#07111c] px-4 py-3 text-sm text-white/72">
                  <input type="checkbox" checked={targetForm.authorization_attestation} onChange={(e) => setTargetForm({ ...targetForm, authorization_attestation: e.target.checked })} />
                  I attest I am authorized to scan this target.
                </label>
              </div>
              <button disabled={!token} className="mt-4 rounded-2xl bg-[#d7f266] px-5 py-3 text-sm font-semibold text-[#102018] disabled:opacity-50">
                Create target
              </button>
            </form>

            <Panel title="Targets" eyebrow="GET /targets">
              {targets.length === 0 ? (
                <EmptyState text="No targets from backend yet." />
              ) : (
                <div className="grid gap-3">
                  {targets.map((target) => (
                    <article key={target.id} className="rounded-[22px] border border-white/10 bg-[#07111c] p-4">
                      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                        <div>
                          <p className="text-lg font-medium text-white">{target.name}</p>
                          <p className="mt-1 break-all text-sm text-white/56">{target.target_url}</p>
                          <p className="mt-2 font-mono text-xs text-white/36">{shortId(target.id)} · {target.target_type}</p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <span className={`rounded-full border border-white/10 px-3 py-1 text-xs ${statusStyle(target.authorization_status)}`}>{target.authorization_status}</span>
                          {target.authorization_status !== "verified" && (
                            <button onClick={() => authorizeTarget(target.id)} className="rounded-full bg-[#d7f266] px-3 py-1 text-xs font-semibold text-[#102018]">Authorize</button>
                          )}
                          <button onClick={() => deleteTarget(target.id)} className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/58 hover:bg-white/10">Delete</button>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </Panel>
          </section>

          <section id="scans" className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
            <form onSubmit={createScan} className="rounded-[30px] border border-white/10 bg-white/6 p-5">
              <p className="text-xs uppercase tracking-[0.3em] text-[#8db39d]">Scans API</p>
              <h3 className="mt-2 text-2xl font-semibold text-white">Launch scan</h3>
              <div className="mt-5 grid gap-3 md:grid-cols-2">
                <select className="field md:col-span-2" value={scanForm.target_id} onChange={(e) => setScanForm({ ...scanForm, target_id: e.target.value })}>
                  <option value="">Choose existing target</option>
                  <option value="__new__">Create inline target during scan</option>
                  {targets.map((target) => <option key={target.id} value={target.id}>{target.name} · {target.authorization_status}</option>)}
                </select>
                {scanForm.target_id === "__new__" && (
                  <>
                    <input className="field" placeholder="Inline target name (optional)" value={scanForm.target_name} onChange={(e) => setScanForm({ ...scanForm, target_name: e.target.value })} />
                    <input className="field" placeholder="Inline target URL/repo" value={scanForm.target_url} onChange={(e) => setScanForm({ ...scanForm, target_url: e.target.value })} />
                  </>
                )}
                <select className="field" value={scanForm.scan_type} onChange={(e) => setScanForm({ ...scanForm, scan_type: e.target.value })}>
                  <option value="url">URL scan</option>
                  <option value="api">API scan</option>
                  <option value="github">Repo/SAST scan</option>
                </select>
                <input className="field" placeholder="Scope override, comma-separated" value={scanForm.scope} onChange={(e) => setScanForm({ ...scanForm, scope: e.target.value })} />
                <label className="md:col-span-2 flex items-center gap-3 rounded-2xl border border-white/10 bg-[#07111c] px-4 py-3 text-sm text-white/72">
                  <input type="checkbox" checked={scanForm.authorization_attestation} onChange={(e) => setScanForm({ ...scanForm, authorization_attestation: e.target.checked })} />
                  Include manual authorization attestation for inline targets.
                </label>
              </div>
              <button disabled={!token} className="mt-4 rounded-2xl bg-[#d7f266] px-5 py-3 text-sm font-semibold text-[#102018] disabled:opacity-50">
                Queue governed scan
              </button>
            </form>

            <Panel title="Scan operations" eyebrow="GET /scans">
              {scans.length === 0 ? (
                <EmptyState text="No scans queued yet." />
              ) : (
                <div className="grid gap-3">
                  {scans.map((scan) => (
                    <button
                      key={scan.id}
                      onClick={() => setSelectedScanId(scan.id)}
                      className={`rounded-[22px] border p-4 text-left transition ${selectedScanId === scan.id ? "border-[#d7f266]/50 bg-[#d7f266]/10" : "border-white/10 bg-[#07111c] hover:bg-white/8"}`}
                    >
                      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                        <div>
                          <p className="font-mono text-xs text-white/36">{shortId(scan.id)} · {scan.scan_type}</p>
                          <p className="mt-2 text-lg font-medium text-white">{scan.summary || "Scan queued"}</p>
                          <p className="mt-2 text-sm text-white/50">Policy decisions: {scan.policy_decisions.length} · Trace nodes: {scan.agent_trace.length}</p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <span className={`rounded-full border border-white/10 px-3 py-1 text-xs ${statusStyle(scan.status)}`}>{scan.status}</span>
                          {scan.status !== "completed" && scan.status !== "cancelled" && (
                            <span onClick={(event) => { event.stopPropagation(); cancelScan(scan.id); }} className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/58 hover:bg-white/10">Cancel</span>
                          )}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </Panel>
          </section>

          <section id="findings" className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
            <Panel title="Risk-ranked findings" eyebrow="GET /findings">
              {activeFindings.length === 0 ? (
                <EmptyState text="No findings persisted for the selected scan yet." />
              ) : (
                <div className="grid gap-3">
                  {activeFindings.map((finding) => (
                    <article key={finding.id} className="rounded-[24px] border border-white/10 bg-[#07111c] p-4">
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div>
                          <div className="flex flex-wrap gap-2">
                            <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${severityStyle(finding.risk_rating)}`}>{finding.risk_rating} · {finding.risk_score}/100</span>
                            <span className={`rounded-full border px-3 py-1 text-xs ${severityStyle(finding.severity)}`}>{finding.severity}</span>
                            <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/54">{finding.status}</span>
                          </div>
                          <h4 className="mt-3 text-xl font-medium text-white">{finding.title}</h4>
                          <p className="mt-2 break-all text-sm text-white/56">{finding.location}</p>
                        </div>
                        <select className="field max-w-[170px]" value={finding.status} onChange={(e) => updateFindingStatus(finding.id, e.target.value)}>
                          <option value="open">open</option>
                          <option value="triaged">triaged</option>
                          <option value="resolved">resolved</option>
                          <option value="ignored">ignored</option>
                        </select>
                      </div>
                      <p className="mt-4 text-sm leading-6 text-white/72">{finding.summary}</p>
                      <p className="mt-3 text-sm leading-6 text-[#d7f266]">{finding.remediation || "No remediation text stored yet."}</p>
                    </article>
                  ))}
                </div>
              )}
            </Panel>

            <section id="reports">
            <Panel title="Selected scan report" eyebrow="Phase 8 exports">
              <div className="rounded-[24px] border border-white/10 bg-[#07111c] p-4">
                <p className="text-sm text-white/56">Target</p>
                <p className="mt-2 break-all text-lg font-medium text-white">{selectedTarget?.target_url || "No scan selected"}</p>
                <p className="mt-3 text-sm text-white/56">Overall risk</p>
                <p className="mt-2 text-4xl font-semibold text-[#d7f266]">
                  {selectedReport?.executive_summary?.overall_risk_score ?? "--"}
                </p>
                <p className="mt-1 text-sm uppercase tracking-[0.24em] text-white/44">
                  {selectedReport?.executive_summary?.overall_risk_rating ?? "pending"}
                </p>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {(["json", "sarif", "pdf", "markdown"] as const).map((kind) => (
                  <button
                    key={kind}
                    type="button"
                    onClick={() => downloadReport(kind)}
                    disabled={!selectedScanId || !token}
                    className={`rounded-2xl border border-white/10 bg-white/6 px-4 py-3 text-center text-sm font-semibold uppercase tracking-[0.18em] text-white/75 transition hover:bg-white/10 ${!selectedScanId ? "pointer-events-none opacity-40" : ""}`}
                  >
                    {kind}
                  </button>
                ))}
              </div>
            </Panel>
            </section>
          </section>

          <section id="audit" className="grid gap-5 xl:grid-cols-[0.8fr_1.2fr]">
            <div id="policy">
            <Panel title="ArmorIQ policy" eyebrow="Signed intent plan">
              <pre className="max-h-[420px] overflow-auto rounded-[22px] border border-white/10 bg-[#050b12] p-4 text-xs leading-6 text-white/68">
                {JSON.stringify(selectedScan?.intent_plan ?? { message: "Select or run a scan to see signed policy scope." }, null, 2)}
              </pre>
            </Panel>
            </div>

            <Panel title="Audit trail" eyebrow="GET /audit">
              {auditEvents.length === 0 ? (
                <EmptyState text="No audit events yet." />
              ) : (
                <div className="grid gap-3">
                  {auditEvents.map((event) => (
                    <article key={event.id} className="rounded-[22px] border border-white/10 bg-[#07111c] p-4">
                      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                        <p className="font-mono text-xs text-[#8db39d]">{event.event_type}</p>
                        <time className="text-xs text-white/36">{new Date(event.created_at).toLocaleString()}</time>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-white/74">{event.message}</p>
                    </article>
                  ))}
                </div>
              )}
            </Panel>
          </section>

          <section id="stream">
            <Panel title="Live scan stream" eyebrow="WS /ws/scans/{scan_id}/stream">
              {streamEvents.length === 0 ? (
                <EmptyState text="Select a scan to watch worker events from the backend WebSocket stream." />
              ) : (
                <div className="grid gap-3">
                  {streamEvents.map((event, index) => (
                    <pre key={`${event}-${index}`} className="overflow-auto rounded-[18px] border border-white/10 bg-[#050b12] p-3 text-xs leading-5 text-white/64">
                      {event}
                    </pre>
                  ))}
                </div>
              )}
            </Panel>
          </section>
        </section>
      </div>
    </main>
  );
}

function Panel({
  title,
  eyebrow,
  children,
}: {
  title: string;
  eyebrow: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-[30px] border border-white/10 bg-white/6 p-5">
      <p className="text-xs uppercase tracking-[0.3em] text-[#8db39d]">{eyebrow}</p>
      <h3 className="mt-2 text-2xl font-semibold text-white">{title}</h3>
      <div className="mt-5">{children}</div>
    </section>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="rounded-[22px] border border-dashed border-white/14 bg-[#07111c] p-6 text-sm text-white/48">
      {text}
    </div>
  );
}
