"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../lib/auth-context";
import { API_BASE, authHeaders, readError, AuditEvent, Scan, shortId } from "../lib/api";
import { Panel, EmptyState } from "../components/ui";

export default function AuditPage() {
  const { token, isLoaded } = useAuth();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [scans, setScans] = useState<Scan[]>([]);
  const [selectedScanId, setSelectedScanId] = useState("");
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState("");

  async function apiFetch<T>(path: string): Promise<T> {
    const r = await fetch(`${API_BASE}${path}`, { headers: authHeaders(token) });
    if (!r.ok) throw new Error(await readError(r));
    return (await r.json()) as T;
  }

  const load = useCallback(async () => {
    if (!token) return;
    const [a, s] = await Promise.all([apiFetch<AuditEvent[]>("/audit/?limit=100"), apiFetch<Scan[]>("/scans/")]);
    setEvents(a); setScans(s);
    setSelectedScanId(prev => prev || s[0]?.id || "");
  }, [token]);

  useEffect(() => { if (!isLoaded) return; load().catch(e => setError(e.message)); }, [load, isLoaded]);

  const selectedScan = scans.find(s => s.id === selectedScanId);

  // Deduplicate event_type prefixes for filter
  const eventTypes = ["all", ...Array.from(new Set(events.map(e => e.event_type.split(".")[0])))];

  const displayed = events.filter(e => filter === "all" || e.event_type.startsWith(filter));

  const policyCount = events.filter(e => e.event_type.startsWith("policy.")).length;
  const scanCount = events.filter(e => e.event_type.startsWith("scan.")).length;

  return (
    <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-[1400px] space-y-5">
        <header className="rounded-2xl border border-white/7 bg-[#080f18] p-6">
          <p className="font-mono text-[10px] uppercase tracking-[0.4em] text-[#a8ff3e]/60">Module 05</p>
          <h1 className="mt-2 font-mono text-3xl font-bold text-white">Policy Ledger</h1>
          <p className="mt-2 font-mono text-xs text-white/35">
            Immutable audit trail for every ArmorIQ enforcement decision, agent action, and policy event.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="rounded-full border border-[#a8ff3e]/20 bg-[#a8ff3e]/6 px-3 py-1 font-mono text-xs text-[#a8ff3e]/70">{policyCount} policy events</span>
            <span className="rounded-full border border-white/10 bg-white/4 px-3 py-1 font-mono text-xs text-white/40">{scanCount} scan events</span>
            <span className="rounded-full border border-white/8 px-3 py-1 font-mono text-xs text-white/30">{events.length} total</span>
          </div>
          {error && <p className="mt-4 rounded-xl border border-[#ff7c70]/20 bg-[#ff7c70]/6 px-4 py-2 font-mono text-xs text-[#ffb3ad]">{error}</p>}
        </header>

        <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
          {/* Audit events */}
          <div className="space-y-4">
            {/* Filters */}
            <div className="flex flex-wrap gap-2">
              {eventTypes.map(type => (
                <button key={type} onClick={() => setFilter(type)}
                  className={`rounded-lg border px-3 py-1.5 font-mono text-xs uppercase tracking-wider transition ${filter === type ? "border-[#a8ff3e]/30 bg-[#a8ff3e]/8 text-[#a8ff3e]" : "border-white/8 text-white/35 hover:border-white/15 hover:text-white/60"}`}>
                  {type}
                </button>
              ))}
            </div>

            <Panel title="Audit trail" eyebrow={`GET /audit · ${displayed.length} shown`}>
              {displayed.length === 0 ? <EmptyState text="No audit events yet." /> : (
                <div className="space-y-2">
                  {displayed.map(event => (
                    <article key={event.id} className="rounded-xl border border-white/6 bg-[#05090f] px-4 py-3">
                      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                        <div className="flex items-center gap-3">
                          <span className={`rounded-md px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${
                            event.event_type.startsWith("policy.") ? "bg-[#a8ff3e]/8 text-[#a8ff3e]/70" :
                            event.event_type.startsWith("scan.") ? "bg-[#3eaaff]/8 text-[#3eaaff]/70" :
                            "bg-white/4 text-white/30"}`}>
                            {event.event_type}
                          </span>
                          {event.scan_id && <span className="font-mono text-[10px] text-white/25">scan:{shortId(event.scan_id)}</span>}
                        </div>
                        <time className="font-mono text-[10px] text-white/20">{new Date(event.created_at).toLocaleString()}</time>
                      </div>
                      <p className="mt-2 font-mono text-xs text-white/55">{event.message}</p>
                    </article>
                  ))}
                </div>
              )}
            </Panel>
          </div>

          {/* Policy sidebar */}
          <div className="space-y-4">
            {/* Scan selector */}
            <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/60 mb-3">Intent plan inspector</p>
              <select className="field" value={selectedScanId} onChange={e => setSelectedScanId(e.target.value)}>
                <option value="">Select a scan</option>
                {scans.map(s => <option key={s.id} value={s.id}>{shortId(s.id)} · {s.scan_type} · {s.status}</option>)}
              </select>
            </div>

            <Panel title="Signed intent plan" eyebrow="ArmorIQ policy">
              <pre className="max-h-[420px] overflow-auto rounded-xl border border-white/7 bg-[#050a0f] p-4 font-mono text-[10px] leading-5 text-white/50">
                {JSON.stringify(selectedScan?.intent_plan ?? { message: "Select a scan to inspect its ArmorIQ intent plan." }, null, 2)}
              </pre>
            </Panel>

            {/* Policy decisions */}
            {selectedScan && selectedScan.policy_decisions.length > 0 && (
              <Panel title="Policy decisions" eyebrow={`${selectedScan.policy_decisions.length} recorded`}>
                <div className="space-y-2">
                  {selectedScan.policy_decisions.map((decision, i) => (
                    <div key={i} className="rounded-xl border border-white/6 bg-[#05090f] p-3">
                      <pre className="font-mono text-[10px] text-white/45 whitespace-pre-wrap">
                        {JSON.stringify(decision, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              </Panel>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}