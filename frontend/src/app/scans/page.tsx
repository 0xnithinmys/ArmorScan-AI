"use client";
 
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useAuth } from "../lib/auth-context";
import {
  API_BASE, authHeaders, readError,
  Target, Scan, ScanCreateResponse, shortId,
} from "../lib/api";
import { Panel, EmptyState, StatusBadge, GreenButton, GhostButton } from "../components/ui";
 
const empty = { target_id: "", target_name: "", target_url: "", scan_type: "url", scope: "", authorization_attestation: true };
 
export default function ScansPage() {
  const { token } = useAuth();
  const [targets, setTargets] = useState<Target[]>([]);
  const [scans, setScans] = useState<Scan[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [form, setForm] = useState(empty);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
 
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
    if (!token) return;
    const [t, s] = await Promise.all([
      apiFetch<Target[]>("/targets/"),
      apiFetch<Scan[]>("/scans/"),
    ]);
    setTargets(t); setScans(s);
    setSelectedId(prev => prev || s[0]?.id || "");
  }, [token]);
 
  useEffect(() => { load().catch(e => setError(e.message)); }, [load]);
 
  async function createScan(e: FormEvent) {
    e.preventDefault(); setError("");
    try {
      const payload = form.target_id === "__new__"
        ? { target_name: form.target_name, target_url: form.target_url, scan_type: form.scan_type, scope: form.scope.split(",").map(s => s.trim()).filter(Boolean), authorization_attestation: form.authorization_attestation }
        : { target_id: form.target_id, scan_type: form.scan_type, scope: form.scope.split(",").map(s => s.trim()).filter(Boolean), authorization_attestation: form.authorization_attestation };
      const res = await apiFetch<ScanCreateResponse>("/scans/", { method: "POST", body: JSON.stringify(payload) });
      setSelectedId(res.scan.id); setForm(empty); await load();
      setMessage("Scan queued. Worker will pick it up if Redis/Celery is online.");
    } catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
  }
 
  async function cancelScan(id: string) {
    setError("");
    try {
      await apiFetch<Scan>(`/scans/${id}/cancel`, { method: "POST" });
      await load(); setMessage("Scan cancelled.");
    } catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
  }
 
  const liveStatuses = new Set(["queued", "planning", "executing", "observing", "reflecting"]);
  const selected = scans.find(s => s.id === selectedId);
 
  return (
    <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-[1400px] space-y-5">
        <header className="rounded-2xl border border-white/7 bg-[#080f18] p-6">
          <p className="font-mono text-[10px] uppercase tracking-[0.4em] text-[#a8ff3e]/60">Module 02</p>
          <h1 className="mt-2 font-mono text-3xl font-bold text-white">Governed Scans</h1>
          <p className="mt-2 font-mono text-xs text-white/35">Queue ArmorIQ-governed scan agents. Every scan is intent-signed before execution.</p>
          {(message || error) && (
            <div className="mt-4 space-y-2">
              {message && <p className="rounded-xl border border-[#a8ff3e]/15 bg-[#a8ff3e]/6 px-4 py-2 font-mono text-xs text-[#a8ff3e]/80">{message}</p>}
              {error && <p className="rounded-xl border border-[#ff7c70]/20 bg-[#ff7c70]/6 px-4 py-2 font-mono text-xs text-[#ffb3ad]">{error}</p>}
            </div>
          )}
        </header>
 
        <div className="grid gap-5 lg:grid-cols-[380px_1fr]">
          {/* Launch form */}
          <form onSubmit={createScan} className="h-fit rounded-2xl border border-white/7 bg-[#080f18] p-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/60">POST /scans</p>
            <h2 className="mt-2 font-mono text-lg font-semibold text-white">Launch scan</h2>
            <div className="mt-5 space-y-3">
              <select className="field" value={form.target_id} onChange={e => setForm({ ...form, target_id: e.target.value })}>
                <option value="">Choose existing target</option>
                <option value="__new__">Inline new target</option>
                {targets.map(t => <option key={t.id} value={t.id}>{t.name} · {t.authorization_status}</option>)}
              </select>
              {form.target_id === "__new__" && (
                <>
                  <input className="field" placeholder="Inline target name" value={form.target_name} onChange={e => setForm({ ...form, target_name: e.target.value })} />
                  <input className="field" placeholder="Inline target URL / repo" value={form.target_url} onChange={e => setForm({ ...form, target_url: e.target.value })} />
                </>
              )}
              <select className="field" value={form.scan_type} onChange={e => setForm({ ...form, scan_type: e.target.value })}>
                <option value="url">URL scan</option>
                <option value="api">API scan</option>
                <option value="github">Repo / SAST scan</option>
              </select>
              <input className="field" placeholder="Scope override, comma-separated" value={form.scope} onChange={e => setForm({ ...form, scope: e.target.value })} />
              <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-white/8 bg-[#05090f] px-4 py-3">
                <input type="checkbox" checked={form.authorization_attestation} onChange={e => setForm({ ...form, authorization_attestation: e.target.checked })} className="accent-[#a8ff3e]" />
                <span className="font-mono text-xs text-white/55">Include manual authorization attestation.</span>
              </label>
              {token ? (
                <GreenButton type="submit" className="w-full justify-center">Queue governed scan</GreenButton>
              ) : (
                <div className="rounded-xl border border-[#a8ff3e]/15 bg-[#a8ff3e]/5 px-4 py-3 text-center">
                  <p className="font-mono text-xs text-[#a8ff3e]/60">
                    Sign in via{" "}
                    <a href="/login" className="underline underline-offset-2 hover:text-[#a8ff3e]">Sign in</a>
                    {" "}first.
                  </p>
                </div>
              )}
            </div>
          </form>
 
          <div className="space-y-5">
            {/* Scan list */}
            <Panel title="Scan queue" eyebrow={`GET /scans · ${scans.length} total`}>
              {scans.length === 0 ? <EmptyState text="No scans queued yet." /> : (
                <div className="space-y-2">
                  {scans.map(scan => (
                    <button key={scan.id} onClick={() => setSelectedId(scan.id)}
                      className={`w-full rounded-xl border p-4 text-left transition ${selectedId === scan.id ? "border-[#a8ff3e]/30 bg-[#a8ff3e]/6" : "border-white/7 bg-[#05090f] hover:bg-[#0c1521]"}`}>
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <p className="font-mono text-[10px] text-white/25">{shortId(scan.id)} · {scan.scan_type}</p>
                          <p className="mt-1 font-mono text-sm text-white">{scan.summary || "Scan queued"}</p>
                          <p className="mt-1 font-mono text-[10px] text-white/30">
                            Policy decisions: {scan.policy_decisions.length} · Trace: {scan.agent_trace.length}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <StatusBadge value={scan.status} />
                          {liveStatuses.has(scan.status) && (
                            <GhostButton onClick={ev => { ev.stopPropagation(); cancelScan(scan.id); }}>Cancel</GhostButton>
                          )}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </Panel>
 
            {/* Selected scan details */}
            {selected && (
              <Panel title="Intent plan" eyebrow={`Scan ${shortId(selected.id)} · ArmorIQ policy`}>
                <pre className="max-h-64 overflow-auto rounded-xl border border-white/7 bg-[#05090f] p-4 font-mono text-xs leading-6 text-white/55">
                  {JSON.stringify(selected.intent_plan ?? { message: "No intent plan yet." }, null, 2)}
                </pre>
              </Panel>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
 