"use client";
 
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useAuth } from "../lib/auth-context";
import {
  API_BASE, authHeaders, readError,
  Target, shortId, statusStyle,
} from "../lib/api";
import {
  Panel, EmptyState, StatusBadge, GreenButton, GhostButton,
} from "../components/ui";
 
const empty = { name: "", target_type: "url", target_url: "", scope: "", authorization_attestation: true };
 
export default function TargetsPage() {
  const { token } = useAuth();
  const [targets, setTargets] = useState<Target[]>([]);
  const [form, setForm] = useState(empty);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
 
  async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
    const r = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        ...(token ? authHeaders(token) : {}),
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
    if (!r.ok) throw new Error(await readError(r));
    if (r.status === 204) return undefined as T;
    return (await r.json()) as T;
  }
 
  const load = useCallback(async () => {
    if (!token) return;
    const data = await apiFetch<Target[]>("/targets/");
    setTargets(data);
  }, [token]);
 
  useEffect(() => { load().catch(e => setError(e.message)); }, [load]);
 
  async function createTarget(e: FormEvent) {
    e.preventDefault(); setError("");
    try {
      await apiFetch<Target>("/targets/", {
        method: "POST",
        body: JSON.stringify({ ...form, scope: form.scope.split(",").map(s => s.trim()).filter(Boolean) }),
      });
      setForm(empty); await load();
      setMessage("Target created.");
    } catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
  }
 
  async function authorizeTarget(id: string) {
    setError("");
    try {
      await apiFetch<Target>(`/targets/${id}/authorize`, {
        method: "POST",
        body: JSON.stringify({ proof_type: "manual_attestation", proof: "I_AM_AUTHORIZED" }),
      });
      await load(); setMessage("Target authorized.");
    } catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
  }
 
  async function deleteTarget(id: string) {
    setError("");
    try {
      await apiFetch<void>(`/targets/${id}`, { method: "DELETE" });
      await load(); setMessage("Target deleted.");
    } catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
  }
 
  return (
    <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-[1400px] space-y-5">
        <header className="rounded-2xl border border-white/7 bg-[#080f18] p-6">
          <p className="font-mono text-[10px] uppercase tracking-[0.4em] text-[#a8ff3e]/60">Module 01</p>
          <h1 className="mt-2 font-mono text-3xl font-bold text-white">Target Registry</h1>
          <p className="mt-2 font-mono text-xs text-white/35">Register scan targets and enforce authorization before any agent touches them.</p>
          {(message || error) && (
            <div className="mt-4 space-y-2">
              {message && <p className="rounded-xl border border-[#a8ff3e]/15 bg-[#a8ff3e]/6 px-4 py-2 font-mono text-xs text-[#a8ff3e]/80">{message}</p>}
              {error && <p className="rounded-xl border border-[#ff7c70]/20 bg-[#ff7c70]/6 px-4 py-2 font-mono text-xs text-[#ffb3ad]">{error}</p>}
            </div>
          )}
        </header>
 
        <div className="grid gap-5 lg:grid-cols-[380px_1fr]">
          {/* Create form */}
          <form onSubmit={createTarget} className="rounded-2xl border border-white/7 bg-[#080f18] p-5 h-fit">
            <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/60">POST /targets</p>
            <h2 className="mt-2 font-mono text-lg font-semibold text-white">Create target</h2>
            <div className="mt-5 space-y-3">
              <input className="field" placeholder="Target name (optional)" value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })} />
              <select className="field" value={form.target_type}
                onChange={e => setForm({ ...form, target_type: e.target.value })}>
                <option value="url">URL</option>
                <option value="api">API</option>
                <option value="github">GitHub / local repo</option>
              </select>
              <input className="field" placeholder="https://example.com or /path/repo" value={form.target_url}
                onChange={e => setForm({ ...form, target_url: e.target.value })} />
              <input className="field" placeholder="Scope hosts, comma-separated" value={form.scope}
                onChange={e => setForm({ ...form, scope: e.target.value })} />
              <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-white/8 bg-[#05090f] px-4 py-3">
                <input type="checkbox" checked={form.authorization_attestation}
                  onChange={e => setForm({ ...form, authorization_attestation: e.target.checked })}
                  className="accent-[#a8ff3e]" />
                <span className="font-mono text-xs text-white/55">I attest I am authorized to scan this target.</span>
              </label>
              {token ? (
                <GreenButton type="submit" className="w-full justify-center">
                  Create target
                </GreenButton>
              ) : (
                <div className="rounded-xl border border-[#a8ff3e]/15 bg-[#a8ff3e]/5 px-4 py-3 text-center">
                  <p className="font-mono text-xs text-[#a8ff3e]/60">
                    Sign in via{" "}
                    <a href="/login" className="underline underline-offset-2 hover:text-[#a8ff3e]">
                      Sign in
                    </a>{" "}
                    to create targets.
                  </p>
                </div>
              )}
            </div>
          </form>
 
          {/* Targets list */}
          <Panel title="Registered targets" eyebrow={`GET /targets · ${targets.length} total`}>
            {targets.length === 0 ? (
              <EmptyState text="No targets registered yet. Create one to begin." />
            ) : (
              <div className="space-y-3">
                {targets.map(target => (
                  <article key={target.id} className="rounded-xl border border-white/7 bg-[#05090f] p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="font-mono text-sm font-semibold text-white">{target.name}</p>
                          <span className="rounded-full border border-white/8 bg-white/4 px-2 py-0.5 font-mono text-[10px] uppercase text-white/35">{target.target_type}</span>
                        </div>
                        <p className="mt-1 truncate font-mono text-xs text-white/40">{target.target_url}</p>
                        <p className="mt-2 font-mono text-[10px] text-white/20">{shortId(target.id)}</p>
                        {target.scope.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {target.scope.map(s => (
                              <span key={s} className="rounded-md border border-white/8 px-2 py-0.5 font-mono text-[10px] text-white/30">{s}</span>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <StatusBadge value={target.authorization_status} />
                        {target.authorization_status !== "verified" && (
                          <GreenButton onClick={() => authorizeTarget(target.id)} className="py-1.5 px-3 text-xs">
                            Authorize
                          </GreenButton>
                        )}
                        <GhostButton onClick={() => deleteTarget(target.id)}>Delete</GhostButton>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </Panel>
        </div>
      </div>
    </main>
  );
}
 
