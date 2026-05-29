"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "../../lib/auth-context";
import {
  API_BASE, authHeaders, readError,
  Target, Scan, Finding,
  shortId, statusStyle, severityStyle,
} from "../../lib/api";
import { StatusBadge, SeverityBadge, GreenButton, GhostButton, EmptyState } from "../../components/ui";

// ── proof method card ─────────────────────────────────────────────────────────
function ProofMethod({ icon, title, desc, active, onClick }: {
  icon: string; title: string; desc: string; active: boolean; onClick: () => void;
}) {
  return (
    <button onClick={onClick}
      className={`w-full rounded-xl border p-4 text-left transition ${active ? "border-[#a8ff3e]/40 bg-[#a8ff3e]/6" : "border-white/7 bg-[#05090f] hover:border-white/15 hover:bg-[#0b1520]"}`}>
      <div className="flex items-start gap-3">
        <span className="text-xl">{icon}</span>
        <div>
          <p className={`font-mono text-xs font-semibold ${active ? "text-[#a8ff3e]" : "text-white/70"}`}>{title}</p>
          <p className="mt-0.5 font-mono text-[10px] text-white/35">{desc}</p>
        </div>
      </div>
    </button>
  );
}

// ── timeline node ─────────────────────────────────────────────────────────────
function TimelineNode({ scan, target }: { scan: Scan; target: Target }) {
  const findingsCount = 0; // would come from aggregated data
  return (
    <Link href={`/scans/${scan.id}`}
      className="group relative flex gap-4 rounded-xl border border-white/6 bg-[#05090f] p-4 transition hover:border-white/12 hover:bg-[#0b1520]">
      <div className="flex flex-col items-center">
        <div className={`h-3 w-3 rounded-full border-2 flex-shrink-0 ${
          scan.status === "completed" ? "border-[#a8ff3e] bg-[#a8ff3e]/20" :
          scan.status === "failed" ? "border-[#ff7c70] bg-[#ff7c70]/20" :
          "border-[#ffd38f] bg-[#ffd38f]/20"
        }`} />
        <div className="mt-1 flex-1 w-px bg-white/6" />
      </div>
      <div className="flex-1 min-w-0 pb-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="font-mono text-xs font-semibold text-white/80 group-hover:text-white">{scan.scan_type} scan</p>
            <p className="font-mono text-[10px] text-white/30">{shortId(scan.id)} · {new Date(scan.created_at).toLocaleString()}</p>
          </div>
          <StatusBadge value={scan.status} />
        </div>
        {scan.summary && <p className="mt-2 font-mono text-[11px] leading-relaxed text-white/45">{scan.summary}</p>}
        <div className="mt-2 flex items-center gap-3">
          <span className="font-mono text-[10px] text-white/25">
            {scan.policy_decisions.length} policy decisions · {scan.agent_trace.length} trace nodes
          </span>
        </div>
      </div>
    </Link>
  );
}

export default function TargetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { token, isLoaded } = useAuth();
  const router = useRouter();
  const [target, setTarget] = useState<Target | null>(null);
  const [scans, setScans] = useState<Scan[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [authProofMethod, setAuthProofMethod] = useState("manual");
  const [proofValue, setProofValue] = useState("");
  const [notes, setNotes] = useState("");
  const [tags, setTags] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [activeTab, setActiveTab] = useState<"overview" | "scans" | "findings" | "auth" | "notes">("overview");

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
    const [t, allScans, allFindings] = await Promise.all([
      apiFetch<Target>(`/targets/${id}`),
      apiFetch<Scan[]>("/scans/"),
      apiFetch<Finding[]>("/findings/"),
    ]);
    setTarget(t);
    setScans(allScans.filter(s => s.target_id === id));
    setFindings(allFindings.filter(f => allScans.filter(s => s.target_id === id).some(s => s.id === f.scan_id)));
  }, [token, id]);

  useEffect(() => {
    if (!isLoaded) return;
    if (!token) { router.push("/login"); return; }
    load().catch(e => setError((e as Error).message));
  }, [token, load, router]);

  async function authorize() {
    setError(""); setMessage("");
    try {
      await apiFetch<Target>(`/targets/${id}/authorize`, {
        method: "POST",
        body: JSON.stringify({ proof_type: authProofMethod, proof: proofValue || "I_AM_AUTHORIZED" }),
      });
      await load();
      setMessage("Target authorized successfully.");
    } catch (err) { setError((err as Error).message); }
  }

  async function deleteTarget() {
    if (!confirm("Delete this target? All associated scans will be orphaned.")) return;
    try {
      await apiFetch<void>(`/targets/${id}`, { method: "DELETE" });
      router.push("/targets");
    } catch (err) { setError((err as Error).message); }
  }

  if (!target) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#04080f]">
        <p className="font-mono text-sm text-white/30">{error || "Loading target..."}</p>
      </main>
    );
  }

  const critCount = findings.filter(f => f.risk_rating === "critical").length;
  const highCount = findings.filter(f => f.risk_rating === "high").length;
  const completedScans = scans.filter(s => s.status === "completed").length;

  const TABS = ["overview", "scans", "findings", "auth", "notes"] as const;

  return (
    <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-[1400px] space-y-5">

        {/* Breadcrumb */}
        <div className="flex items-center gap-2 font-mono text-xs text-white/30">
          <Link href="/targets" className="hover:text-white/60 transition">Targets</Link>
          <span>/</span>
          <span className="text-white/60">{target.name}</span>
        </div>

        {/* Header */}
        <div className="rounded-2xl border border-white/7 bg-[#080f18] p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-md border border-white/8 bg-white/4 px-2 py-1 font-mono text-[10px] uppercase text-white/40">{target.target_type}</span>
                <StatusBadge value={target.authorization_status} />
              </div>
              <h1 className="mt-3 font-mono text-3xl font-bold text-white">{target.name}</h1>
              <p className="mt-1 font-mono text-sm text-white/40 break-all">{target.target_url}</p>
              <p className="mt-2 font-mono text-[10px] text-white/20">ID: {target.id} · created {new Date(target.created_at).toLocaleDateString()}</p>
            </div>
            <div className="flex flex-wrap gap-2 flex-shrink-0">
              <Link href={`/scans?target=${id}`}
                className="rounded-xl bg-[#a8ff3e] px-4 py-2.5 font-mono text-xs font-bold text-[#040a06] transition hover:bg-[#bfff61]">
                + New scan
              </Link>
              <GhostButton onClick={deleteTarget}>Delete</GhostButton>
            </div>
          </div>

          {/* Inline stat pills */}
          <div className="mt-5 flex flex-wrap gap-3">
            {[
              { label: "Scans run", value: scans.length },
              { label: "Completed", value: completedScans },
              { label: "Critical findings", value: critCount },
              { label: "High findings", value: highCount },
              { label: "Scope entries", value: target.scope.length },
            ].map(s => (
              <div key={s.label} className="rounded-lg border border-white/7 bg-[#05090f] px-3 py-2">
                <p className="font-mono text-[10px] text-white/30">{s.label}</p>
                <p className="font-mono text-lg font-bold text-white">{s.value}</p>
              </div>
            ))}
          </div>

          {(message || error) && (
            <div className="mt-4 space-y-2">
              {message && <p className="rounded-xl border border-[#a8ff3e]/15 bg-[#a8ff3e]/6 px-4 py-2 font-mono text-xs text-[#a8ff3e]/80">{message}</p>}
              {error && <p className="rounded-xl border border-[#ff7c70]/20 bg-[#ff7c70]/6 px-4 py-2 font-mono text-xs text-[#ffb3ad]">{error}</p>}
            </div>
          )}
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
              {tab === "scans" && scans.length > 0 && (
                <span className="ml-1.5 rounded-full bg-white/10 px-1.5 py-0.5 text-[9px]">{scans.length}</span>
              )}
            </button>
          ))}
        </div>

        {/* ── Overview tab ──────────────────────────────────────────────────── */}
        {activeTab === "overview" && (
          <div className="grid gap-4 lg:grid-cols-2">

            {/* Scope / attack surface */}
            <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50">Attack surface</p>
              <h3 className="mt-1 font-mono text-base font-semibold text-white">Scope entries</h3>
              <div className="mt-4">
                {target.scope.length === 0 ? (
                  <p className="font-mono text-xs text-white/25">No scope defined. All sub-paths in scope.</p>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {target.scope.map(s => (
                      <span key={s} className="rounded-lg border border-white/8 bg-[#05090f] px-3 py-1.5 font-mono text-xs text-white/60">{s}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Auth proof status */}
            <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50">Authorization</p>
              <h3 className="mt-1 font-mono text-base font-semibold text-white">Ownership proof</h3>
              <div className="mt-4 space-y-3">
                <div className="flex items-center gap-3">
                  <div className={`h-3 w-3 rounded-full flex-shrink-0 ${target.authorization_status === "verified" ? "bg-[#a8ff3e] shadow-[0_0_8px_#a8ff3e]" : "bg-[#ffaaa4]"}`} />
                  <div>
                    <p className={`font-mono text-sm font-semibold ${target.authorization_status === "verified" ? "text-[#a8ff3e]" : "text-[#ffaaa4]"}`}>
                      {target.authorization_status === "verified" ? "Authorized" : "Pending authorization"}
                    </p>
                    {target.authorization_proof_type && (
                      <p className="font-mono text-[10px] text-white/30">Method: {target.authorization_proof_type}</p>
                    )}
                  </div>
                </div>
                {target.authorization_status !== "verified" && (
                  <button onClick={() => setActiveTab("auth")}
                    className="font-mono text-xs text-[#a8ff3e]/60 underline underline-offset-2 hover:text-[#a8ff3e]">
                    Authorize this target →
                  </button>
                )}
              </div>
            </div>

            {/* Last scan summary */}
            {scans.length > 0 && (
              <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5 lg:col-span-2">
                <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50">Last scan</p>
                <h3 className="mt-1 font-mono text-base font-semibold text-white">Most recent result</h3>
                <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-mono text-sm text-white">{scans[0].summary || "No summary available"}</p>
                    <p className="mt-1 font-mono text-[10px] text-white/30">{new Date(scans[0].created_at).toLocaleString()} · {scans[0].scan_type}</p>
                  </div>
                  <Link href={`/scans/${scans[0].id}`}>
                    <StatusBadge value={scans[0].status} />
                  </Link>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Scans tab ─────────────────────────────────────────────────────── */}
        {activeTab === "scans" && (
          <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50">Scan history</p>
            <h3 className="mt-1 mb-4 font-mono text-base font-semibold text-white">{scans.length} scans total</h3>
            {scans.length === 0 ? <EmptyState text="No scans run for this target yet." /> : (
              <div className="space-y-2">
                {scans.map(s => <TimelineNode key={s.id} scan={s} target={target} />)}
              </div>
            )}
          </div>
        )}

        {/* ── Findings tab ──────────────────────────────────────────────────── */}
        {activeTab === "findings" && (
          <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50">Vulnerability findings</p>
            <h3 className="mt-1 mb-4 font-mono text-base font-semibold text-white">{findings.length} findings</h3>
            {findings.length === 0 ? <EmptyState text="No findings associated with this target." /> : (
              <div className="space-y-2">
                {findings.map(f => (
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

        {/* ── Auth tab ──────────────────────────────────────────────────────── */}
        {activeTab === "auth" && (
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50">Ownership verification</p>
              <h3 className="mt-1 mb-4 font-mono text-base font-semibold text-white">Authorize target</h3>
              <div className="space-y-3">
                {[
                  { id: "manual", icon: "✋", title: "Manual attestation", desc: "Assert you own or have written permission to test this target." },
                  { id: "dns_txt", icon: "🌐", title: "DNS TXT record", desc: "Add a TXT record to your domain to prove ownership." },
                  { id: "http_file", icon: "📄", title: "HTTP file proof", desc: "Upload a verification file to /.well-known/armorscan.txt" },
                  { id: "github_org", icon: "🐙", title: "GitHub org proof", desc: "Verify via GitHub org membership or repo admin access." },
                ].map(m => (
                  <ProofMethod key={m.id} icon={m.icon} title={m.title} desc={m.desc}
                    active={authProofMethod === m.id} onClick={() => setAuthProofMethod(m.id)} />
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50">Proof details</p>
              <h3 className="mt-1 mb-4 font-mono text-base font-semibold text-white capitalize">{authProofMethod.replace("_", " ")}</h3>

              {authProofMethod === "manual" && (
                <div className="space-y-3">
                  <div className="rounded-xl border border-[#ffd38f]/15 bg-[#ffd38f]/5 px-4 py-3">
                    <p className="font-mono text-xs text-[#ffd38f]/80">
                      By proceeding, you confirm you are authorized to perform security testing against this target and that you hold written permission from the owner.
                    </p>
                  </div>
                  <GreenButton onClick={authorize} className="w-full justify-center">
                    Confirm & authorize
                  </GreenButton>
                </div>
              )}

              {authProofMethod === "dns_txt" && (
                <div className="space-y-3">
                  <p className="font-mono text-xs text-white/45">Add this TXT record to your DNS:</p>
                  <div className="rounded-xl border border-white/8 bg-[#05090f] p-3">
                    <p className="font-mono text-[11px] text-[#a8ff3e]/80 break-all">armorscan-verify={shortId(id)}</p>
                  </div>
                  <p className="font-mono text-xs text-white/30">Paste the record value below to confirm:</p>
                  <input className="field" placeholder="armorscan-verify=..." value={proofValue} onChange={e => setProofValue(e.target.value)} />
                  <GreenButton onClick={authorize} className="w-full justify-center">Verify DNS record</GreenButton>
                </div>
              )}

              {authProofMethod === "http_file" && (
                <div className="space-y-3">
                  <p className="font-mono text-xs text-white/45">Upload this file to your web server:</p>
                  <div className="rounded-xl border border-white/8 bg-[#05090f] p-3">
                    <p className="font-mono text-[11px] text-white/60">Path: <span className="text-[#a8ff3e]/80">/.well-known/armorscan.txt</span></p>
                    <p className="mt-1 font-mono text-[11px] text-white/60">Content: <span className="text-[#a8ff3e]/80">{shortId(id)}-verified</span></p>
                  </div>
                  <GreenButton onClick={authorize} className="w-full justify-center">Check file & authorize</GreenButton>
                </div>
              )}

              {authProofMethod === "github_org" && (
                <div className="space-y-3">
                  <p className="font-mono text-xs text-white/45">Enter your GitHub org or repo path:</p>
                  <input className="field" placeholder="org/repo or org-name" value={proofValue} onChange={e => setProofValue(e.target.value)} />
                  <GreenButton onClick={authorize} className="w-full justify-center">Verify GitHub access</GreenButton>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Notes tab ─────────────────────────────────────────────────────── */}
        {activeTab === "notes" && (
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50">Target notes</p>
              <h3 className="mt-1 mb-4 font-mono text-base font-semibold text-white">Internal notes</h3>
              <textarea value={notes} onChange={e => setNotes(e.target.value)}
                placeholder="Add context, scope clarifications, special credentials notes..."
                rows={8}
                className="field resize-none w-full" />
              <GreenButton className="mt-3" onClick={() => setMessage("Notes saved locally.")}>Save notes</GreenButton>
            </div>
            <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50">Tags</p>
              <h3 className="mt-1 mb-4 font-mono text-base font-semibold text-white">Labels & categorization</h3>
              <input className="field" placeholder="production, pci-scope, bug-bounty, ..." value={tags} onChange={e => setTags(e.target.value)} />
              <div className="mt-3 flex flex-wrap gap-2">
                {tags.split(",").filter(t => t.trim()).map(tag => (
                  <span key={tag} className="rounded-lg border border-[#a8ff3e]/20 bg-[#a8ff3e]/6 px-3 py-1 font-mono text-xs text-[#a8ff3e]/80">{tag.trim()}</span>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}