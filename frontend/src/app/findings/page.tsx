"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../lib/auth-context";
import { API_BASE, authHeaders, readError, Finding, Scan, shortId } from "../lib/api";
import { Panel, EmptyState, SeverityBadge, StatusBadge, PageLoader } from "../components/ui";

export default function FindingsPage() {
  const { token, isLoaded } = useAuth();
  const [findings, setFindings] = useState<Finding[]>([]);
  const [scans, setScans] = useState<Scan[]>([]);
  const [filterScan, setFilterScan] = useState("all");
  const [filterSeverity, setFilterSeverity] = useState("all");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
    const r = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { ...(token ? authHeaders(token) : {}), "Content-Type": "application/json", ...options.headers },
    });
    if (!r.ok) throw new Error(await readError(r));
    return (await r.json()) as T;
  }

  const load = useCallback(async () => {
    if (!token) { setIsLoading(false); return; }
    const [f, s] = await Promise.all([apiFetch<Finding[]>("/findings/"), apiFetch<Scan[]>("/scans/")]);
    setFindings(f); setScans(s);
    setIsLoading(false);
  }, [token]);

  useEffect(() => { if (!isLoaded) return; load().catch(e => setError(e.message)); }, [load, isLoaded]);

  async function updateStatus(id: string, status: string) {
    setError("");
    try {
      await apiFetch<Finding>(`/findings/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
      await load(); setMessage("Finding updated.");
    } catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
  }

  const displayed = findings.filter(f => {
    const scanMatch = filterScan === "all" || f.scan_id === filterScan;
    const sevMatch = filterSeverity === "all" || f.severity.toLowerCase() === filterSeverity;
    return scanMatch && sevMatch;
  });

  const critCount = findings.filter(f => f.risk_rating === "critical").length;
  const highCount = findings.filter(f => f.risk_rating === "high").length;

  if (isLoading) return <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6"><div className="mx-auto max-w-[1400px] space-y-5"><div className="h-[120px] rounded-2xl bg-[#080f18] animate-pulse"></div><div className="h-[400px] rounded-2xl bg-[#080f18] animate-pulse"></div></div></main>;

  return (
    <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-[1400px] space-y-5">
        <header className="rounded-2xl border border-white/7 bg-[#080f18] p-6">
          <p className="font-mono text-[10px] uppercase tracking-[0.4em] text-[#a8ff3e]/60">Module 03</p>
          <h1 className="mt-2 font-mono text-3xl font-bold text-white">Risk Triage</h1>
          <p className="mt-2 font-mono text-xs text-white/35">Browse, filter, and triage AI-discovered vulnerabilities sorted by risk score.</p>
          {/* Summary badges */}
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="rounded-full border border-[#ff7c70]/30 bg-[#5f1919]/40 px-3 py-1 font-mono text-xs text-[#ffb3ad]">{critCount} critical</span>
            <span className="rounded-full border border-[#ffb15f]/30 bg-[#5e3512]/40 px-3 py-1 font-mono text-xs text-[#ffd8ad]">{highCount} high</span>
            <span className="rounded-full border border-white/10 bg-white/4 px-3 py-1 font-mono text-xs text-white/40">{findings.length} total</span>
          </div>
          {(message || error) && (
            <div className="mt-4 space-y-2">
              {message && <p className="rounded-xl border border-[#a8ff3e]/15 bg-[#a8ff3e]/6 px-4 py-2 font-mono text-xs text-[#a8ff3e]/80">{message}</p>}
              {error && <p className="rounded-xl border border-[#ff7c70]/20 bg-[#ff7c70]/6 px-4 py-2 font-mono text-xs text-[#ffb3ad]">{error}</p>}
            </div>
          )}
        </header>

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <select className="field max-w-[220px]" value={filterScan} onChange={e => setFilterScan(e.target.value)}>
            <option value="all">All scans</option>
            {scans.map(s => <option key={s.id} value={s.id}>{shortId(s.id)} · {s.scan_type}</option>)}
          </select>
          <select className="field max-w-[160px]" value={filterSeverity} onChange={e => setFilterSeverity(e.target.value)}>
            <option value="all">All severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <span className="self-center font-mono text-xs text-white/30">{displayed.length} shown</span>
        </div>

        <Panel title="Findings" eyebrow="GET /findings">
          {displayed.length === 0 ? (
            <EmptyState text="No findings match the current filters." />
          ) : (
            <div className="space-y-4">
              {displayed.map(finding => (
                <article key={finding.id} className="rounded-xl border border-white/7 bg-[#05090f] p-5">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap gap-2">
                        <SeverityBadge rating={finding.risk_rating} score={finding.risk_score} />
                        <SeverityBadge rating={finding.severity} />
                        <StatusBadge value={finding.status} />
                        <span className="rounded-full border border-white/8 px-2 py-0.5 font-mono text-[10px] text-white/30">
                          confidence {Math.round(finding.confidence * 100)}%
                        </span>
                      </div>
                      <h3 className="mt-3 font-mono text-base font-semibold text-white">{finding.title}</h3>
                      <p className="mt-1 truncate font-mono text-xs text-white/40">{finding.location}</p>
                      <p className="mt-3 text-sm leading-relaxed text-white/60" style={{ fontFamily: "var(--font-serif)" }}>
                        {finding.summary}
                      </p>
                      {finding.remediation && (
                        <p className="mt-3 text-sm leading-relaxed text-[#a8ff3e]/70" style={{ fontFamily: "var(--font-serif)" }}>
                          ↳ {finding.remediation}
                        </p>
                      )}
                    </div>
                    <div className="flex-shrink-0">
                      <select
                        value={finding.status}
                        onChange={e => updateStatus(finding.id, e.target.value)}
                        className="field w-[150px]"
                      >
                        <option value="open">open</option>
                        <option value="triaged">triaged</option>
                        <option value="resolved">resolved</option>
                        <option value="ignored">ignored</option>
                      </select>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </Panel>
      </div>
    </main>
  );
}