"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../lib/auth-context";
import { API_BASE, authHeaders, readError, Scan, Target, shortId } from "../lib/api";
import { Panel, EmptyState, StatusBadge, GhostButton } from "../components/ui";

const FORMATS = ["json", "sarif", "pdf", "markdown"] as const;
type Format = typeof FORMATS[number];

export default function ReportsPage() {
  const { token, isLoaded } = useAuth();
  const [scans, setScans] = useState<Scan[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function apiFetch<T>(path: string): Promise<T> {
    const r = await fetch(`${API_BASE}${path}`, { headers: authHeaders(token) });
    if (!r.ok) throw new Error(await readError(r));
    return (await r.json()) as T;
  }

  const load = useCallback(async () => {
    if (!token) return;
    const [s, t] = await Promise.all([apiFetch<Scan[]>("/scans/"), apiFetch<Target[]>("/targets/")]);
    setScans(s); setTargets(t);
    setSelectedId(prev => prev || s[0]?.id || "");
  }, [token]);

  useEffect(() => { if (!isLoaded) return; load().catch(e => setError(e.message)); }, [load, isLoaded]);

  async function downloadReport(kind: Format) {
    if (!selectedId) return;
    setError(""); setMessage("");
    try {
      const r = await fetch(`${API_BASE}/reports/${selectedId}/${kind}`, { headers: authHeaders(token) });
      if (!r.ok) throw new Error(await readError(r));
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `armorscan-${selectedId}.${kind === "markdown" ? "md" : kind}`;
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
      setMessage(`${kind.toUpperCase()} report downloaded.`);
    } catch (err) { setError(err instanceof Error ? err.message : "Download failed"); }
  }

  const selected = scans.find(s => s.id === selectedId);
  const selectedTarget = selected ? targets.find(t => t.id === selected.target_id) : null;
  const report = selected?.report_json?.risk_report as
    | { executive_summary?: { overall_risk_score?: number; overall_risk_rating?: string } }
    | undefined;

  return (
    <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-[1400px] space-y-5">
        <header className="rounded-2xl border border-white/7 bg-[#080f18] p-6">
          <p className="font-mono text-[10px] uppercase tracking-[0.4em] text-[#a8ff3e]/60">Module 04</p>
          <h1 className="mt-2 font-mono text-3xl font-bold text-white">Report Exports</h1>
          <p className="mt-2 font-mono text-xs text-white/35">Generate and download SARIF, JSON, PDF, and Markdown reports for any completed scan.</p>
          {(message || error) && (
            <div className="mt-4 space-y-2">
              {message && <p className="rounded-xl border border-[#a8ff3e]/15 bg-[#a8ff3e]/6 px-4 py-2 font-mono text-xs text-[#a8ff3e]/80">{message}</p>}
              {error && <p className="rounded-xl border border-[#ff7c70]/20 bg-[#ff7c70]/6 px-4 py-2 font-mono text-xs text-[#ffb3ad]">{error}</p>}
            </div>
          )}
        </header>

        <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
          {/* Scan selector */}
          <Panel title="Select scan" eyebrow={`${scans.length} scans available`}>
            {scans.length === 0 ? <EmptyState text="No scans available for reporting yet." /> : (
              <div className="space-y-2">
                {scans.map(scan => (
                  <button key={scan.id} onClick={() => setSelectedId(scan.id)}
                    className={`w-full rounded-xl border p-4 text-left transition ${selectedId === scan.id ? "border-[#a8ff3e]/30 bg-[#a8ff3e]/6" : "border-white/7 bg-[#05090f] hover:bg-[#0c1521]"}`}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-mono text-[10px] text-white/25">{shortId(scan.id)} · {scan.scan_type}</p>
                        <p className="mt-1 font-mono text-sm text-white">{scan.summary || "Scan queued"}</p>
                        <p className="mt-1 font-mono text-[10px] text-white/25">{new Date(scan.created_at).toLocaleString()}</p>
                      </div>
                      <StatusBadge value={scan.status} />
                    </div>
                  </button>
                ))}
              </div>
            )}
          </Panel>

          {/* Report panel */}
          <div className="space-y-4">
            <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/60">Selected scan</p>
              {selected ? (
                <>
                  <p className="mt-3 font-mono text-sm font-semibold text-white">{shortId(selected.id)}</p>
                  <p className="mt-1 font-mono text-xs text-white/40 truncate">
                    {selectedTarget?.target_url || "Unknown target"}
                  </p>
                  <div className="mt-4">
                    <p className="font-mono text-[10px] text-white/30 uppercase tracking-wider">Overall risk</p>
                    <p className="mt-1 font-mono text-5xl font-bold text-[#a8ff3e]">
                      {report?.executive_summary?.overall_risk_score ?? "—"}
                    </p>
                    <p className="mt-1 font-mono text-xs uppercase tracking-widest text-white/35">
                      {report?.executive_summary?.overall_risk_rating ?? "pending"}
                    </p>
                  </div>
                </>
              ) : (
                <p className="mt-3 font-mono text-sm text-white/30">No scan selected</p>
              )}
            </div>

            <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/60 mb-4">Export formats</p>
              <div className="grid grid-cols-2 gap-2">
                {FORMATS.map(kind => (
                  <button key={kind} onClick={() => downloadReport(kind)}
                    disabled={!selectedId || !token}
                    className="rounded-xl border border-white/8 bg-[#05090f] px-4 py-4 text-center transition hover:border-[#a8ff3e]/25 hover:bg-[#0c1521] disabled:cursor-not-allowed disabled:opacity-40 group">
                    <p className="font-mono text-sm font-bold uppercase tracking-widest text-white/60 group-hover:text-white/90">{kind}</p>
                    <p className="mt-1 font-mono text-[10px] text-white/25">
                      {kind === "json" && "raw data"}
                      {kind === "sarif" && "ci/cd"}
                      {kind === "pdf" && "executive"}
                      {kind === "markdown" && "docs"}
                    </p>
                  </button>
                ))}
              </div>
            </div>

            {/* Raw report JSON */}
            {selected?.report_json && (
              <Panel title="Report JSON" eyebrow="raw payload">
                <pre className="max-h-48 overflow-auto rounded-xl border border-white/7 bg-[#05090f] p-4 font-mono text-[10px] leading-5 text-white/45">
                  {JSON.stringify(selected.report_json, null, 2)}
                </pre>
              </Panel>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}