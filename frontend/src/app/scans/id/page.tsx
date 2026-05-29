"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "../../lib/auth-context";
import {
  API_BASE, authHeaders, readError,
  Target, Scan, Finding,
  shortId, statusStyle, severityStyle,
} from "../../lib/api";
import { StatusBadge, SeverityBadge, GreenButton, GhostButton, EmptyState } from "../../components/ui";

const LIVE_STATUSES = new Set(["queued", "planning", "executing", "observing", "reflecting"]);

// ── phase timeline ────────────────────────────────────────────────────────────
const PHASES = ["queued", "planning", "executing", "observing", "reflecting", "completed"];

function PhaseTimeline({ currentStatus }: { currentStatus: string }) {
  const currentIdx = PHASES.indexOf(currentStatus);
  const isFailed = currentStatus === "failed" || currentStatus === "cancelled";

  return (
    <div className="flex items-center gap-0">
      {PHASES.map((phase, i) => {
        const done = !isFailed && i < currentIdx;
        const active = !isFailed && i === currentIdx;
        const failed = isFailed && i <= Math.max(currentIdx, 1);

        return (
          <div key={phase} className="flex flex-1 items-center">
            <div className="flex flex-col items-center gap-1.5">
              <div className={`relative h-3 w-3 rounded-full border-2 transition-all ${
                failed ? "border-[#ff7c70] bg-[#ff7c70]/20" :
                done ? "border-[#a8ff3e] bg-[#a8ff3e]" :
                active ? "border-[#ffd38f] bg-[#ffd38f]/30 shadow-[0_0_8px_rgba(255,211,143,0.4)]" :
                "border-white/15 bg-transparent"
              }`}>
                {active && <div className="absolute inset-0 rounded-full animate-ping bg-[#ffd38f]/30" />}
              </div>
              <p className={`font-mono text-[9px] uppercase ${
                active ? "text-[#ffd38f]" : done ? "text-[#a8ff3e]/60" : "text-white/20"
              }`}>{phase}</p>
            </div>
            {i < PHASES.length - 1 && (
              <div className={`mx-0.5 h-px flex-1 transition-all ${done || (active && i < currentIdx) ? "bg-[#a8ff3e]/40" : "bg-white/8"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── engine card ───────────────────────────────────────────────────────────────
function EngineCard({ name, icon, status, findings, desc }: {
  name: string; icon: string; status: "complete" | "running" | "pending" | "skipped";
  findings: number; desc: string;
}) {
  return (
    <div className={`rounded-xl border p-4 transition ${
      status === "complete" ? "border-[#a8ff3e]/20 bg-[#a8ff3e]/4" :
      status === "running" ? "border-[#ffd38f]/25 bg-[#ffd38f]/4" :
      status === "skipped" ? "border-white/5 bg-white/2 opacity-40" :
      "border-white/7 bg-[#05090f]"
    }`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="text-base">{icon}</span>
          <div>
            <p className={`font-mono text-xs font-semibold ${
              status === "complete" ? "text-[#a8ff3e]" :
              status === "running" ? "text-[#ffd38f]" :
              "text-white/50"
            }`}>{name}</p>
            <p className="font-mono text-[10px] text-white/30">{desc}</p>
          </div>
        </div>
        <div className="text-right flex-shrink-0">
          <p className={`font-mono text-[10px] uppercase ${
            status === "complete" ? "text-[#a8ff3e]/60" :
            status === "running" ? "text-[#ffd38f]/60" :
            "text-white/20"
          }`}>{status}</p>
          {findings > 0 && <p className="font-mono text-sm font-bold text-white">{findings}</p>}
        </div>
      </div>
      {status === "running" && (
        <div className="mt-3 h-0.5 w-full overflow-hidden rounded-full bg-white/6">
          <div className="h-full w-2/3 animate-pulse rounded-full bg-[#ffd38f]/50" />
        </div>
      )}
    </div>
  );
}

// ── trace node ────────────────────────────────────────────────────────────────
function TraceNode({ node, index }: { node: Record<string, unknown>; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const type = (node.type as string) || "action";
  const content = (node.content as string) || JSON.stringify(node).slice(0, 80);

  return (
    <div className="rounded-xl border border-white/6 bg-[#05090f]">
      <button onClick={() => setExpanded(e => !e)}
        className="flex w-full items-start gap-3 px-4 py-3 text-left">
        <span className="font-mono text-[10px] text-white/25 flex-shrink-0 pt-0.5">#{String(index + 1).padStart(2, "0")}</span>
        <span className={`rounded px-1.5 py-0.5 font-mono text-[9px] uppercase flex-shrink-0 ${
          type === "tool_use" ? "bg-[#8bd8ff]/8 text-[#8bd8ff]/70" :
          type === "tool_result" ? "bg-[#a8ff3e]/8 text-[#a8ff3e]/70" :
          "bg-white/5 text-white/30"
        }`}>{type}</span>
        <p className="flex-1 font-mono text-[11px] text-white/50 line-clamp-1">{content}</p>
        <span className="font-mono text-[10px] text-white/20">{expanded ? "▲" : "▼"}</span>
      </button>
      {expanded && (
        <pre className="border-t border-white/5 px-4 py-3 font-mono text-[10px] leading-5 text-white/40 overflow-auto max-h-48">
          {JSON.stringify(node, null, 2)}
        </pre>
      )}
    </div>
  );
}

export default function ScanDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { token } = useAuth();
  const router = useRouter();
  const [scan, setScan] = useState<Scan | null>(null);
  const [target, setTarget] = useState<Target | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [activeTab, setActiveTab] = useState<"timeline" | "engines" | "findings" | "evidence" | "policy">("timeline");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
    const r = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { ...(token ? authHeaders(token) : {}), "Content-Type": "application/json", ...options.headers },
    });
    if (!r.ok) throw new Error(await readError(r));
    if (r.status === 204) return undefined as T;
    return (await r.json()) as T;
  }

  const load = useCallback(async () => {
    if (!token || !id) return;
    const [allScans, allTargets, allFindings] = await Promise.all([
      apiFetch<Scan[]>("/scans/"),
      apiFetch<Target[]>("/targets/"),
      apiFetch<Finding[]>("/findings/"),
    ]);
    const s = allScans.find(x => x.id === id);
    if (!s) { setError("Scan not found"); return; }
    setScan(s);
    setTarget(allTargets.find(t => t.id === s.target_id) || null);
    setFindings(allFindings.filter(f => f.scan_id === id));
  }, [token, id]);

  // auto-poll while live
  useEffect(() => {
    if (!token) { router.push("/login"); return; }
    load().catch(e => setError((e as Error).message));
  }, [token, load, router]);

  useEffect(() => {
    if (!scan) return;
    if (LIVE_STATUSES.has(scan.status)) {
      pollRef.current = setInterval(() => load().catch(() => {}), 4000);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [scan?.status, load]);

  async function cancelScan() {
    setError(""); setMessage("");
    try {
      await apiFetch<Scan>(`/scans/${id}/cancel`, { method: "POST" });
      await load(); setMessage("Scan cancel requested.");
    } catch (err) { setError((err as Error).message); }
  }

  if (!scan) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#04080f]">
        <p className="font-mono text-sm text-white/30">{error || "Loading scan..."}</p>
      </main>
    );
  }

  const isLive = LIVE_STATUSES.has(scan.status);
  const TABS = ["timeline", "engines", "findings", "evidence", "policy"] as const;

  // derive engine statuses from scan_type and status
  const dastStatus = scan.scan_type === "url" || scan.scan_type === "api" ?
    (scan.status === "completed" ? "complete" : isLive ? "running" : "pending") : "skipped";
  const sastStatus = scan.scan_type === "github" ?
    (scan.status === "completed" ? "complete" : isLive ? "running" : "pending") : "skipped";
  const secretsStatus = scan.scan_type === "github" ?
    (scan.status === "completed" ? "complete" : "pending") : "skipped";

  return (
    <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-[1400px] space-y-5">

        {/* Breadcrumb */}
        <div className="flex items-center gap-2 font-mono text-xs text-white/30">
          <Link href="/scans" className="hover:text-white/60 transition">Scans</Link>
          <span>/</span>
          <span className="text-white/60">{shortId(scan.id)}</span>
        </div>

        {/* Header */}
        <div className="rounded-2xl border border-white/7 bg-[#080f18] p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-md border border-white/8 bg-white/4 px-2 py-1 font-mono text-[10px] uppercase text-white/40">{scan.scan_type}</span>
                <StatusBadge value={scan.status} />
                {isLive && (
                  <span className="flex items-center gap-1.5 rounded-full border border-[#ffd38f]/20 bg-[#ffd38f]/6 px-3 py-1 font-mono text-[10px] text-[#ffd38f]">
                    <span className="h-1.5 w-1.5 rounded-full bg-[#ffd38f] animate-pulse" />
                    live
                  </span>
                )}
              </div>
              <h1 className="mt-3 font-mono text-2xl font-bold text-white">
                {target?.name || shortId(scan.target_id)} scan
              </h1>
              {target && <p className="mt-1 font-mono text-sm text-white/40 break-all">{target.target_url}</p>}
              <p className="mt-2 font-mono text-[10px] text-white/20">
                {shortId(scan.id)} · started {scan.started_at ? new Date(scan.started_at).toLocaleString() : "not yet"}
                {scan.completed_at && ` · completed ${new Date(scan.completed_at).toLocaleString()}`}
              </p>
            </div>
            <div className="flex flex-wrap gap-2 flex-shrink-0">
              {isLive && <GhostButton onClick={cancelScan}>Cancel scan</GhostButton>}
              {scan.status === "completed" && (
                <Link href="/reports" className="rounded-xl border border-white/8 bg-white/4 px-4 py-2.5 font-mono text-xs text-white/60 transition hover:bg-white/8">
                  Export report →
                </Link>
              )}
            </div>
          </div>

          {/* Phase timeline */}
          <div className="mt-6">
            <PhaseTimeline currentStatus={scan.status} />
          </div>

          {scan.summary && (
            <p className="mt-4 font-mono text-xs text-white/50 rounded-xl border border-white/7 bg-[#05090f] px-4 py-3">
              {scan.summary}
            </p>
          )}

          {(message || error) && (
            <div className="mt-4 space-y-2">
              {message && <p className="rounded-xl border border-[#a8ff3e]/15 bg-[#a8ff3e]/6 px-4 py-2 font-mono text-xs text-[#a8ff3e]/80">{message}</p>}
              {error && <p className="rounded-xl border border-[#ff7c70]/20 bg-[#ff7c70]/6 px-4 py-2 font-mono text-xs text-[#ffb3ad]">{error}</p>}
            </div>
          )}
        </div>

        {/* Stat pills */}
        <div className="flex flex-wrap gap-3">
          {[
            { label: "Findings", value: findings.length },
            { label: "Critical", value: findings.filter(f => f.risk_rating === "critical").length },
            { label: "Policy decisions", value: scan.policy_decisions.length },
            { label: "Agent trace nodes", value: scan.agent_trace.length },
            { label: "Scope entries", value: scan.scope.length },
          ].map(s => (
            <div key={s.label} className="rounded-xl border border-white/7 bg-[#080f18] px-4 py-2.5">
              <p className="font-mono text-[10px] text-white/30">{s.label}</p>
              <p className="font-mono text-xl font-bold text-white">{s.value}</p>
            </div>
          ))}
        </div>

        {/* Tab nav */}
        <div className="flex gap-1 overflow-x-auto rounded-xl border border-white/7 bg-[#080f18] p-1">
          {TABS.map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className={`rounded-lg px-4 py-2 font-mono text-xs capitalize transition whitespace-nowrap ${activeTab === tab ? "bg-[#a8ff3e]/10 text-[#a8ff3e]" : "text-white/35 hover:text-white/60"}`}>
              {tab}
              {tab === "findings" && findings.length > 0 && (
                <span className="ml-1.5 rounded-full bg-white/10 px-1.5 py-0.5 text-[9px]">{findings.length}</span>
              )}
            </button>
          ))}
        </div>

        {/* ── Timeline tab ──────────────────────────────────────────────────── */}
        {activeTab === "timeline" && (
          <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50 mb-4">Agent trace · {scan.agent_trace.length} nodes</p>
            {scan.agent_trace.length === 0 ? (
              <EmptyState text="No trace nodes yet. Trace appears as the agent runs." />
            ) : (
              <div className="space-y-1.5">
                {scan.agent_trace.map((node, i) => <TraceNode key={i} node={node} index={i} />)}
              </div>
            )}
          </div>
        )}

        {/* ── Engines tab ───────────────────────────────────────────────────── */}
        {activeTab === "engines" && (
          <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50 mb-4">Engine-by-engine progress</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <EngineCard name="ZAP / DAST" icon="🔍" status={dastStatus} findings={findings.filter(f => f.risk_factors?.engine === "zap").length || 0} desc="Dynamic web app scanning" />
              <EngineCard name="Semgrep / SAST" icon="🔬" status={sastStatus} findings={findings.filter(f => f.risk_factors?.engine === "semgrep").length || 0} desc="Static source code analysis" />
              <EngineCard name="Gitleaks" icon="🔐" status={secretsStatus} findings={findings.filter(f => f.risk_factors?.engine === "gitleaks").length || 0} desc="Secret & credential scanning" />
              <EngineCard name="Nuclei" icon="⚡" status={scan.status === "completed" ? "complete" : isLive ? "running" : "pending"} findings={findings.filter(f => f.risk_factors?.engine === "nuclei").length || 0} desc="CVE & template-based probes" />
              <EngineCard name="Bandit" icon="🐍" status={scan.scan_type === "github" && scan.status === "completed" ? "complete" : "skipped"} findings={0} desc="Python security linting" />
              <EngineCard name="Trivy" icon="🛡️" status={scan.scan_type === "github" && scan.status === "completed" ? "complete" : "skipped"} findings={0} desc="Dependency & container CVEs" />
            </div>
          </div>
        )}

        {/* ── Findings tab ──────────────────────────────────────────────────── */}
        {activeTab === "findings" && (
          <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50 mb-4">Discovered findings · {findings.length} total</p>
            {findings.length === 0 ? <EmptyState text="No findings discovered in this scan yet." /> : (
              <div className="space-y-2">
                {findings
                  .sort((a, b) => b.risk_score - a.risk_score)
                  .map(f => (
                    <Link key={f.id} href={`/findings/${f.id}`}
                      className="group flex items-center gap-3 rounded-xl border border-white/6 bg-[#05090f] px-4 py-3 transition hover:border-white/12 hover:bg-[#0b1520]">
                      <SeverityBadge rating={f.risk_rating} score={f.risk_score} />
                      <div className="min-w-0 flex-1">
                        <p className="font-mono text-xs font-semibold text-white/80 truncate group-hover:text-white">{f.title}</p>
                        <p className="font-mono text-[10px] text-white/30 truncate">{f.location}</p>
                      </div>
                      <span className={`font-mono text-[10px] flex-shrink-0 ${statusStyle(f.status)}`}>{f.status}</span>
                    </Link>
                  ))}
              </div>
            )}
          </div>
        )}

        {/* ── Evidence tab ──────────────────────────────────────────────────── */}
        {activeTab === "evidence" && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50 mb-4">Discovered routes & forms</p>
              {scan.report_json ? (
                <pre className="max-h-96 overflow-auto rounded-xl border border-white/7 bg-[#05090f] p-4 font-mono text-[10px] leading-5 text-white/45">
                  {JSON.stringify(scan.report_json, null, 2)}
                </pre>
              ) : (
                <EmptyState text="No evidence collected yet. Evidence appears after the scan completes." />
              )}
            </div>
          </div>
        )}

        {/* ── Policy tab ────────────────────────────────────────────────────── */}
        {activeTab === "policy" && (
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50 mb-4">Signed intent plan</p>
              <pre className="max-h-80 overflow-auto rounded-xl border border-white/7 bg-[#05090f] p-4 font-mono text-[10px] leading-5 text-white/45">
                {JSON.stringify(scan.intent_plan ?? { message: "No intent plan." }, null, 2)}
              </pre>
            </div>
            <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50 mb-4">Policy decisions · {scan.policy_decisions.length}</p>
              {scan.policy_decisions.length === 0 ? <EmptyState text="No policy decisions recorded." /> : (
                <div className="space-y-2">
                  {scan.policy_decisions.map((d, i) => (
                    <div key={i} className="rounded-xl border border-white/6 bg-[#05090f] p-3">
                      <pre className="font-mono text-[10px] leading-5 text-white/40 whitespace-pre-wrap">
                        {JSON.stringify(d, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

      </div>
    </main>
  );
}