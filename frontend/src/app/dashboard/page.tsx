"use client";

import { useCallback, useEffect, useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "../lib/auth-context";
import {
  API_BASE, authHeaders, readError,
  User, Target, Scan, Finding, AuditEvent,
  shortId, severityStyle, statusStyle,
} from "../lib/api";
import { EmptyState, StatusBadge, SeverityBadge, GreenButton } from "../components/ui";

// ── tiny chart component ──────────────────────────────────────────────────────
function SparkBar({ values, color = "#a8ff3e" }: { values: number[]; color?: string }) {
  const max = Math.max(...values, 1);
  return (
    <div className="flex h-8 items-end gap-[2px]">
      {values.map((v, i) => (
        <div
          key={i}
          className="flex-1 rounded-sm transition-all"
          style={{ height: `${Math.max(4, (v / max) * 100)}%`, backgroundColor: color, opacity: 0.55 + (i / values.length) * 0.45 }}
        />
      ))}
    </div>
  );
}

function DonutRing({ segments }: { segments: { value: number; color: string; label: string }[] }) {
  const total = segments.reduce((a, s) => a + s.value, 0) || 1;
  let offset = 0;
  const r = 28; const circ = 2 * Math.PI * r;
  return (
    <svg width="72" height="72" viewBox="0 0 72 72">
      {segments.map((seg, i) => {
        const dash = (seg.value / total) * circ;
        const el = (
          <circle key={i} cx="36" cy="36" r={r}
            fill="none" stroke={seg.color} strokeWidth="10"
            strokeDasharray={`${dash} ${circ - dash}`}
            strokeDashoffset={-offset * circ / total - circ * 0.25}
            style={{ transition: "stroke-dasharray 0.5s ease" }} />
        );
        offset += seg.value;
        return el;
      })}
      <circle cx="36" cy="36" r="22" fill="#080f18" />
    </svg>
  );
}

// ── stat card ─────────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, href, accent = false, trend }: {
  label: string; value: string | number; sub: string; href: string; accent?: boolean; trend?: number[];
}) {
  return (
    <Link href={href} className="group relative overflow-hidden rounded-2xl border border-white/7 bg-[#080f18] p-5 transition hover:border-[#a8ff3e]/25 hover:bg-[#0b1520]">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(168,255,62,0.04),transparent_60%)] opacity-0 transition group-hover:opacity-100" />
      <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-white/35">{label}</p>
      <p className={`mt-2 font-mono text-4xl font-bold ${accent ? "text-[#a8ff3e]" : "text-white"}`}>{value}</p>
      <p className="mt-1 font-mono text-[11px] text-white/40">{sub}</p>
      {trend && <div className="mt-3"><SparkBar values={trend} /></div>}
    </Link>
  );
}

// ── section header ────────────────────────────────────────────────────────────
function SectionHeader({ eyebrow, title, action }: { eyebrow: string; title: string; action?: { label: string; href: string } }) {
  return (
    <div className="flex items-end justify-between">
      <div>
        <p className="font-mono text-[10px] uppercase tracking-[0.4em] text-[#a8ff3e]/50">{eyebrow}</p>
        <h2 className="mt-1 font-mono text-lg font-semibold text-white">{title}</h2>
      </div>
      {action && (
        <Link href={action.href} className="font-mono text-xs text-white/30 transition hover:text-[#a8ff3e]">{action.label} →</Link>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const { token, clearToken } = useAuth();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [targets, setTargets] = useState<Target[]>([]);
  const [scans, setScans] = useState<Scan[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  const load = useCallback(async (tok = token) => {
    if (!tok) return;
    const req = async <T,>(path: string) => {
      const r = await fetch(`${API_BASE}${path}`, { headers: authHeaders(tok) });
      if (!r.ok) throw new Error(await readError(r));
      return (await r.json()) as T;
    };
    const [me, t, s, f, a] = await Promise.all([
      req<User>("/auth/me"),
      req<Target[]>("/targets/"),
      req<Scan[]>("/scans/"),
      req<Finding[]>("/findings/"),
      req<AuditEvent[]>("/audit/?limit=20"),
    ]);
    setUser(me); setTargets(t); setScans(s); setFindings(f); setAuditEvents(a);
  }, [token]);

  useEffect(() => {
    if (!token) { router.push("/login"); return; }
    startTransition(() => {
      load(token).catch((e: Error) => {
        setError(e.message);
        if (e.message.includes("401") || e.message.includes("403")) { clearToken(); router.push("/login"); }
      });
    });
  }, [token, load, router, clearToken]);

  // ── derived metrics ──────────────────────────────────────────────────────
  const liveStatuses = new Set(["queued", "planning", "executing", "observing", "reflecting"]);
  const verifiedTargets = targets.filter(t => t.authorization_status === "verified").length;
  const activeScans = scans.filter(s => liveStatuses.has(s.status)).length;
  const critFindings = findings.filter(f => f.risk_rating === "critical").length;
  const highFindings = findings.filter(f => f.risk_rating === "high").length;
  const openFindings = findings.filter(f => f.status === "open").length;
  const resolvedFindings = findings.filter(f => f.status === "resolved").length;

  // fake 7-day sparklines from real counts (distribute across buckets)
  const scanTrend = Array.from({ length: 7 }, (_, i) =>
    scans.filter(s => {
      const d = new Date(s.created_at); const now = new Date();
      return (now.getTime() - d.getTime()) < (i + 1) * 86400000 * 1.2;
    }).length
  );

  // severity donut data
  const severitySegments = [
    { value: critFindings, color: "#ff7c70", label: "Critical" },
    { value: highFindings, color: "#ffb15f", label: "High" },
    { value: findings.filter(f => f.risk_rating === "medium").length, color: "#e2eb72", label: "Medium" },
    { value: findings.filter(f => f.risk_rating === "low").length, color: "#8bd8ff", label: "Low" },
  ];

  // engine coverage mock (real would come from scan report_json)
  const engines = [
    { name: "ZAP / DAST", runs: scans.filter(s => s.scan_type === "url").length, color: "#a8ff3e" },
    { name: "Semgrep / SAST", runs: scans.filter(s => s.scan_type === "github").length, color: "#8bd8ff" },
    { name: "API Probe", runs: scans.filter(s => s.scan_type === "api").length, color: "#ffb15f" },
    { name: "Gitleaks", runs: scans.filter(s => s.scan_type === "github").length, color: "#ff7c70" },
  ];

  const recentFindings = findings
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  const recentScans = scans
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 4);

  // auth proof breakdown
  const unverifiedTargets = targets.filter(t => t.authorization_status !== "verified");

  return (
    <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-[1600px] space-y-6">

        {/* ── Page header ─────────────────────────────────────────────────── */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.4em] text-[#a8ff3e]/50">Security dashboard</p>
            <h1 className="mt-1 font-mono text-2xl font-bold text-white">
              {user ? `${user.full_name}` : "Loading..."}
            </h1>
            {user && <p className="mt-0.5 font-mono text-xs text-white/30">{user.email}</p>}
          </div>
          <div className="flex items-center gap-3">
            {error && <span className="font-mono text-xs text-[#ffb3ad]">{error}</span>}
            <GreenButton
              disabled={!token || isPending}
              onClick={() => startTransition(() => { load().catch(e => setError((e as Error).message)); })}
            >
              {isPending ? "↻ syncing..." : "↻ refresh"}
            </GreenButton>
          </div>
        </div>

        {/* ── Top stat row ─────────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard label="Targets" value={targets.length} sub={`${verifiedTargets} verified · ${unverifiedTargets.length} pending auth`} href="/targets" trend={[targets.length, targets.length, targets.length, targets.length, targets.length, targets.length, targets.length]} />
          <StatCard label="Total scans" value={scans.length} sub={`${activeScans} active now`} href="/scans" trend={scanTrend} />
          <StatCard label="Open findings" value={openFindings} sub={`${critFindings} critical · ${highFindings} high`} href="/findings" accent={critFindings > 0} trend={[openFindings, openFindings, openFindings, openFindings, openFindings, openFindings, openFindings]} />
          <StatCard label="Resolved" value={resolvedFindings} sub={`${findings.length} total findings`} href="/findings" />
        </div>

        {/* ── Middle row: severity + engine + target health ─────────────── */}
        <div className="grid gap-4 lg:grid-cols-3">

          {/* Severity breakdown */}
          <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50">Severity distribution</p>
            <h3 className="mt-1 font-mono text-base font-semibold text-white">Finding risk profile</h3>
            <div className="mt-4 flex items-center gap-5">
              {findings.length > 0 ? (
                <>
                  <DonutRing segments={severitySegments} />
                  <div className="flex-1 space-y-2">
                    {severitySegments.map(s => (
                      <div key={s.label} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="h-2 w-2 rounded-full" style={{ backgroundColor: s.color }} />
                          <span className="font-mono text-xs text-white/50">{s.label}</span>
                        </div>
                        <span className="font-mono text-xs font-semibold text-white">{s.value}</span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <p className="font-mono text-xs text-white/25 py-4">No findings yet.</p>
              )}
            </div>
          </div>

          {/* Engine coverage */}
          <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50">Engine coverage</p>
            <h3 className="mt-1 font-mono text-base font-semibold text-white">Scanner utilization</h3>
            <div className="mt-4 space-y-3">
              {engines.map(e => {
                const pct = scans.length > 0 ? Math.round((e.runs / Math.max(scans.length, 1)) * 100) : 0;
                return (
                  <div key={e.name}>
                    <div className="mb-1 flex items-center justify-between">
                      <span className="font-mono text-[11px] text-white/50">{e.name}</span>
                      <span className="font-mono text-[11px] font-semibold" style={{ color: e.color }}>{e.runs} runs</span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/6">
                      <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, backgroundColor: e.color }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Target auth health */}
          <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50">Authorization health</p>
            <h3 className="mt-1 font-mono text-base font-semibold text-white">Target proof status</h3>
            {targets.length === 0 ? (
              <p className="mt-4 font-mono text-xs text-white/25">No targets registered.</p>
            ) : (
              <div className="mt-4 space-y-2">
                {/* Summary bar */}
                <div className="h-2 w-full overflow-hidden rounded-full bg-white/6">
                  <div className="h-full rounded-full bg-[#a8ff3e] transition-all duration-700"
                    style={{ width: `${(verifiedTargets / targets.length) * 100}%` }} />
                </div>
                <p className="font-mono text-xs text-white/35">{verifiedTargets}/{targets.length} targets authorized</p>
                {/* Unverified list */}
                {unverifiedTargets.length > 0 && (
                  <div className="mt-3 space-y-1.5">
                    {unverifiedTargets.slice(0, 3).map(t => (
                      <Link key={t.id} href={`/targets/${t.id}`}
                        className="flex items-center justify-between rounded-lg border border-[#ffaaa4]/15 bg-[#3a1010]/40 px-3 py-2 transition hover:border-[#ffaaa4]/30">
                        <span className="font-mono text-xs text-white/60 truncate">{t.name}</span>
                        <span className="font-mono text-[10px] text-[#ffaaa4] ml-2 flex-shrink-0">needs auth</span>
                      </Link>
                    ))}
                    {unverifiedTargets.length > 3 && (
                      <Link href="/targets" className="font-mono text-[10px] text-white/25 hover:text-[#a8ff3e]">
                        +{unverifiedTargets.length - 3} more →
                      </Link>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── Active scans + recent findings ───────────────────────────────── */}
        <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">

          {/* Recent findings */}
          <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
            <SectionHeader eyebrow="Live threat feed" title="Recent findings" action={{ label: "All findings", href: "/findings" }} />
            <div className="mt-4 space-y-2">
              {recentFindings.length === 0 ? (
                <EmptyState text="No findings surfaced yet." />
              ) : recentFindings.map(f => (
                <Link key={f.id} href={`/findings/${f.id}`}
                  className="group flex items-center gap-3 rounded-xl border border-white/6 bg-[#05090f] px-3 py-3 transition hover:border-white/12 hover:bg-[#0b1520]">
                  <span className={`rounded-md border px-2 py-0.5 font-mono text-[10px] uppercase font-semibold flex-shrink-0 ${severityStyle(f.risk_rating)}`}>
                    {f.risk_rating}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="font-mono text-xs font-semibold text-white/80 truncate group-hover:text-white">{f.title}</p>
                    <p className="font-mono text-[10px] text-white/30 truncate">{f.location}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1 flex-shrink-0">
                    <span className={`font-mono text-[10px] ${statusStyle(f.status)}`}>{f.status}</span>
                    <span className="font-mono text-[10px] text-white/20">{f.risk_score}/100</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>

          {/* Recent scans */}
          <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
            <SectionHeader eyebrow="Scan activity" title="Recent scans" action={{ label: "All scans", href: "/scans" }} />
            <div className="mt-4 space-y-2">
              {recentScans.length === 0 ? (
                <EmptyState text="No scans queued yet." />
              ) : recentScans.map(s => {
                const target = targets.find(t => t.id === s.target_id);
                return (
                  <Link key={s.id} href={`/scans/${s.id}`}
                    className="group flex flex-col gap-2 rounded-xl border border-white/6 bg-[#05090f] px-3 py-3 transition hover:border-white/12 hover:bg-[#0b1520]">
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0">
                        <p className="font-mono text-xs font-semibold text-white/80 truncate group-hover:text-white">
                          {target?.name || shortId(s.target_id)}
                        </p>
                        <p className="font-mono text-[10px] text-white/30">{shortId(s.id)} · {s.scan_type}</p>
                      </div>
                      <StatusBadge value={s.status} />
                    </div>
                    {liveStatuses.has(s.status) && (
                      <div className="h-0.5 w-full overflow-hidden rounded-full bg-white/6">
                        <div className="h-full w-1/2 animate-pulse rounded-full bg-[#ffd38f]" />
                      </div>
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        </div>

        {/* ── Audit + export activity ───────────────────────────────────────── */}
        <div className="grid gap-4 lg:grid-cols-[0.7fr_1.3fr]">

          {/* Report/export activity */}
          <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
            <SectionHeader eyebrow="Report activity" title="Export status" action={{ label: "Reports", href: "/reports" }} />
            <div className="mt-4 space-y-2">
              {scans.filter(s => s.report_json).length === 0 ? (
                <EmptyState text="No reports generated yet." />
              ) : scans.filter(s => s.report_json).slice(0, 4).map(s => {
                const report = s.report_json?.risk_report as { executive_summary?: { overall_risk_score?: number; overall_risk_rating?: string } } | undefined;
                return (
                  <Link key={s.id} href={`/reports`}
                    className="group flex items-center justify-between rounded-xl border border-white/6 bg-[#05090f] px-3 py-3 transition hover:border-white/12">
                    <div>
                      <p className="font-mono text-xs text-white/60">{shortId(s.id)}</p>
                      <p className="font-mono text-[10px] text-white/30">{new Date(s.created_at).toLocaleDateString()}</p>
                    </div>
                    <span className="font-mono text-xs font-bold text-[#a8ff3e]">
                      {report?.executive_summary?.overall_risk_score ?? "—"}/100
                    </span>
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Audit trail */}
          <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
            <SectionHeader eyebrow="Policy ledger" title="Audit trail" action={{ label: "Full ledger", href: "/audit" }} />
            <div className="mt-4 space-y-1.5">
              {auditEvents.length === 0 ? (
                <EmptyState text="No audit events yet." />
              ) : auditEvents.slice(0, 8).map(ev => (
                <div key={ev.id} className="flex items-start gap-3 rounded-xl border border-white/5 bg-[#05090f] px-3 py-2.5">
                  <span className={`mt-0.5 flex-shrink-0 rounded px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider ${
                    ev.event_type.startsWith("policy.") ? "bg-[#a8ff3e]/8 text-[#a8ff3e]/70" :
                    ev.event_type.startsWith("scan.") ? "bg-[#8bd8ff]/8 text-[#8bd8ff]/70" :
                    "bg-white/4 text-white/30"
                  }`}>{ev.event_type}</span>
                  <p className="flex-1 font-mono text-[11px] leading-relaxed text-white/45 line-clamp-1">{ev.message}</p>
                  <time className="flex-shrink-0 font-mono text-[9px] text-white/20">{new Date(ev.created_at).toLocaleTimeString()}</time>
                </div>
              ))}
            </div>
          </div>
        </div>

      </div>
    </main>
  );
}