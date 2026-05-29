"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "../../lib/auth-context";
import {
  API_BASE, authHeaders, readError,
  Finding, Scan, Target,
  shortId, severityStyle, statusStyle,
} from "../../lib/api";
import { SeverityBadge, StatusBadge, GreenButton, GhostButton, EmptyState } from "../../components/ui";

// ── CVSS meter ────────────────────────────────────────────────────────────────
function RiskMeter({ score, label }: { score: number; label: string }) {
  const color = score >= 90 ? "#ff7c70" : score >= 70 ? "#ffb15f" : score >= 40 ? "#e2eb72" : "#8bd8ff";
  const angle = (score / 100) * 180;

  return (
    <div className="flex flex-col items-center">
      <svg width="100" height="56" viewBox="0 0 100 56">
        <path d="M10 50 A40 40 0 0 1 90 50" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" strokeLinecap="round" />
        <path d="M10 50 A40 40 0 0 1 90 50" fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
          strokeDasharray={`${(score / 100) * 125.66} 125.66`} style={{ transition: "stroke-dasharray 0.8s ease" }} />
        <text x="50" y="48" textAnchor="middle" fill="white" fontSize="14" fontFamily="monospace" fontWeight="bold">{score}</text>
      </svg>
      <p className="font-mono text-[10px] text-white/35 uppercase tracking-wider">{label}</p>
    </div>
  );
}

// ── code block ────────────────────────────────────────────────────────────────
function CodeBlock({ title, content, language = "text" }: { title: string; content: string; language?: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(content).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1500); });
  };
  return (
    <div className="rounded-xl border border-white/7 overflow-hidden">
      <div className="flex items-center justify-between border-b border-white/7 bg-[#05090f] px-4 py-2">
        <span className="font-mono text-[10px] text-white/40">{title}</span>
        <button onClick={copy} className="font-mono text-[10px] text-white/30 hover:text-[#a8ff3e] transition">
          {copied ? "copied ✓" : "copy"}
        </button>
      </div>
      <pre className="max-h-56 overflow-auto bg-[#030609] p-4 font-mono text-[11px] leading-5 text-white/60 whitespace-pre-wrap">
        {content}
      </pre>
    </div>
  );
}

// ── status history item ───────────────────────────────────────────────────────
function StatusHistoryItem({ status, label, timestamp, active }: {
  status: string; label: string; timestamp?: string; active: boolean;
}) {
  return (
    <div className={`flex items-start gap-3 ${active ? "" : "opacity-40"}`}>
      <div className={`mt-1 h-2 w-2 rounded-full flex-shrink-0 ${active ? "bg-[#a8ff3e]" : "bg-white/20"}`} />
      <div>
        <p className={`font-mono text-xs font-semibold ${active ? "text-white" : "text-white/50"}`}>{label}</p>
        {timestamp && <p className="font-mono text-[10px] text-white/25">{timestamp}</p>}
      </div>
    </div>
  );
}

export default function FindingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { token, isLoaded } = useAuth();
  const router = useRouter();
  const [finding, setFinding] = useState<Finding | null>(null);
  const [scan, setScan] = useState<Scan | null>(null);
  const [target, setTarget] = useState<Target | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"overview" | "evidence" | "remediation" | "history">("overview");
  const [fpReason, setFpReason] = useState("");
  const [showFpForm, setShowFpForm] = useState(false);
  const [commentText, setCommentText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
    const r = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { ...(token ? authHeaders(token) : {}), "Content-Type": "application/json", ...options.headers },
    });
    if (!r.ok) throw new Error(await readError(r));
    return (await r.json()) as T;
  }

  const load = useCallback(async () => {
    if (!token || !id) return;
    try {
      const f = await apiFetch<any>(`/findings/${id}`);
      setFinding(f);
      if (f.scan) setScan(f.scan);
      if (f.scan?.target) setTarget(f.scan.target);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Finding not found");
    } finally {
      setIsLoading(false);
    }
  }, [token, id]);

  useEffect(() => {
    if (!isLoaded) return;
    if (!token) { router.push("/login"); return; }
    load().catch(e => setError((e as Error).message));
  }, [token, load, router]);

  async function updateStatus(status: string) {
    setError(""); setMessage("");
    try {
      await apiFetch<Finding>(`/findings/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
      await load(); setMessage(`Status updated to "${status}".`);
    } catch (err) { setError((err as Error).message); }
  }

  async function markFalsePositive() {
    setError(""); setMessage(""); setIsSubmitting(true);
    try {
      await apiFetch<any>(`/findings/${id}/suppressions`, { method: "POST", body: JSON.stringify({ reason: fpReason }) });
      await load(); setMessage("Marked as false positive."); setShowFpForm(false);
    } catch (err) { setError((err as Error).message); }
    finally { setIsSubmitting(false); }
  }

  async function submitComment() {
    if (!commentText.trim()) return;
    setError(""); setMessage(""); setIsSubmitting(true);
    try {
      await apiFetch<any>(`/findings/${id}/comments`, { method: "POST", body: JSON.stringify({ body: commentText }) });
      await load(); setMessage("Comment added."); setCommentText("");
    } catch (err) { setError((err as Error).message); }
    finally { setIsSubmitting(false); }
  }

  if (isLoading || !finding) {
    return (
      <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
        <div className="mx-auto max-w-[1400px] space-y-5">
          <header className="rounded-2xl border border-white/7 bg-[#080f18] p-6 h-[140px] animate-pulse" />
          <div className="grid gap-5 lg:grid-cols-[1.4fr_0.6fr]">
            <div className="h-[400px] rounded-2xl border border-white/7 bg-[#080f18] animate-pulse" />
            <div className="h-[600px] rounded-2xl border border-white/7 bg-[#080f18] animate-pulse" />
          </div>
        </div>
      </main>
    );
  }

  const TABS = ["overview", "evidence", "remediation", "history"] as const;

  // derive some mock evidence from available data
  const hasReproSteps = finding.reproduction_steps.length > 0;
  const riskFactorKeys = Object.keys(finding.risk_factors);

  return (
    <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-[1400px] space-y-5">

        {/* Breadcrumb */}
        <div className="flex items-center gap-2 font-mono text-xs text-white/30">
          <Link href="/findings" className="hover:text-white/60 transition">Findings</Link>
          <span>/</span>
          {scan && <Link href={`/scans/${scan.id}`} className="hover:text-white/60 transition">scan:{shortId(scan.id)}</Link>}
          {scan && <span>/</span>}
          <span className="text-white/60">{shortId(finding.id)}</span>
        </div>

        {/* Header */}
        <div className="rounded-2xl border border-white/7 bg-[#080f18] p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <SeverityBadge rating={finding.risk_rating} score={finding.risk_score} />
                <SeverityBadge rating={finding.severity} />
                <StatusBadge value={finding.status} />
                <span className="rounded-full border border-white/8 px-2 py-0.5 font-mono text-[10px] text-white/30">
                  {Math.round(finding.confidence * 100)}% confidence
                </span>
              </div>
              <h1 className="mt-3 font-mono text-2xl font-bold text-white leading-tight">{finding.title}</h1>
              <p className="mt-2 font-mono text-sm text-white/40 break-all">{finding.location}</p>
              {target && (
                <p className="mt-1 font-mono text-[10px] text-white/25">
                  Target: <Link href={`/targets/${target.id}`} className="text-white/40 hover:text-white/70 transition">{target.name}</Link>
                  {scan && <> · Scan: <Link href={`/scans/${scan.id}`} className="text-white/40 hover:text-white/70 transition">{shortId(scan.id)}</Link></>}
                </p>
              )}
            </div>

            {/* Score meter */}
            <div className="flex-shrink-0">
              <RiskMeter score={finding.risk_score} label="risk score" />
            </div>
          </div>

          {/* Quick action bar */}
          <div className="mt-5 flex flex-wrap items-center gap-2">
            {["open", "triaged", "resolved", "ignored"].map(s => (
              <button key={s} onClick={() => updateStatus(s)}
                className={`rounded-lg border px-3 py-1.5 font-mono text-xs capitalize transition ${
                  finding.status === s
                    ? "border-[#a8ff3e]/30 bg-[#a8ff3e]/8 text-[#a8ff3e]"
                    : "border-white/8 text-white/35 hover:border-white/20 hover:text-white/60"
                }`}>{s}</button>
            ))}
            <button onClick={() => setShowFpForm(v => !v)}
              className="rounded-lg border border-[#ffb3ad]/20 bg-[#ffb3ad]/4 px-3 py-1.5 font-mono text-xs text-[#ffb3ad]/70 transition hover:bg-[#ffb3ad]/8">
              False positive
            </button>
          </div>

          {showFpForm && (
            <div className="mt-3 flex flex-col gap-2 sm:flex-row">
              <input className="field flex-1" placeholder="Reason for false positive..." value={fpReason} onChange={e => setFpReason(e.target.value)} />
              <GreenButton isLoading={isSubmitting} disabled={isSubmitting || !fpReason.trim()} onClick={markFalsePositive}>Confirm FP</GreenButton>
              <GhostButton onClick={() => setShowFpForm(false)}>Cancel</GhostButton>
            </div>
          )}

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
            </button>
          ))}
        </div>

        {/* ── Overview tab ──────────────────────────────────────────────────── */}
        {activeTab === "overview" && (
          <div className="grid gap-4 lg:grid-cols-[1.4fr_0.6fr]">
            <div className="space-y-4">
              {/* Summary */}
              <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
                <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50 mb-3">Summary</p>
                <p className="text-sm leading-7 text-white/65" style={{ fontFamily: "var(--font-serif)" }}>{finding.summary}</p>
              </div>

              {/* Business impact */}
              {finding.business_impact && (
                <div className="rounded-2xl border border-[#ffb15f]/15 bg-[#ffb15f]/4 p-5">
                  <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#ffb15f]/60 mb-3">Business impact</p>
                  <p className="text-sm leading-7 text-white/65" style={{ fontFamily: "var(--font-serif)" }}>{finding.business_impact}</p>
                </div>
              )}

              {/* Location */}
              <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
                <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50 mb-3">Location</p>
                <div className="rounded-xl border border-white/7 bg-[#05090f] px-4 py-3">
                  <p className="font-mono text-xs text-white/70 break-all">{finding.location}</p>
                </div>
              </div>
            </div>

            {/* Risk factors sidebar */}
            <div className="space-y-4">
              <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
                <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50 mb-3">Risk factors</p>
                {riskFactorKeys.length === 0 ? (
                  <p className="font-mono text-xs text-white/25">No risk factors recorded.</p>
                ) : (
                  <div className="space-y-2">
                    {riskFactorKeys.map(key => (
                      <div key={key} className="flex items-start justify-between gap-2">
                        <span className="font-mono text-[11px] text-white/40 capitalize">{key.replace(/_/g, " ")}</span>
                        <span className="font-mono text-[11px] text-white/70 text-right">{String(finding.risk_factors[key])}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Metadata */}
              <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
                <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50 mb-3">Metadata</p>
                <div className="space-y-2">
                  {[
                    { label: "Finding ID", value: shortId(finding.id) },
                    { label: "Scan ID", value: scan ? shortId(scan.id) : "—" },
                    { label: "Discovered", value: new Date(finding.created_at).toLocaleDateString() },
                    { label: "Confidence", value: `${Math.round(finding.confidence * 100)}%` },
                    { label: "Risk score", value: `${finding.risk_score}/100` },
                  ].map(m => (
                    <div key={m.label} className="flex items-center justify-between">
                      <span className="font-mono text-[10px] text-white/30">{m.label}</span>
                      <span className="font-mono text-[10px] text-white/60">{m.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Evidence tab ──────────────────────────────────────────────────── */}
        {activeTab === "evidence" && (
          <div className="space-y-4">
            {hasReproSteps ? (
              <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
                <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50 mb-4">Reproduction steps</p>
                <div className="space-y-2">
                  {finding.reproduction_steps.map((step, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <span className="flex-shrink-0 rounded-md bg-white/6 px-2 py-0.5 font-mono text-[10px] text-white/40">{i + 1}</span>
                      <p className="font-mono text-xs leading-relaxed text-white/60">{step}</p>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
                <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50 mb-4">HTTP evidence</p>
                <div className="grid gap-4 lg:grid-cols-2">
                  <CodeBlock title="Request" content={`GET ${finding.location} HTTP/1.1\nHost: ${target?.target_url?.replace(/https?:\/\//, "") || "target"}\nUser-Agent: ArmorScan/1.0\nAccept: */*\n\n[Request body if applicable]`} />
                  <CodeBlock title="Response" content={`HTTP/1.1 200 OK\nContent-Type: text/html\nServer: nginx\n\n[Response body excerpt — evidence stored in report_json]\n\nNote: full request/response evidence is attached to the scan report.`} />
                </div>
              </div>
            )}

            {/* Risk factors as evidence */}
            {riskFactorKeys.length > 0 && (
              <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
                <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50 mb-4">Structured evidence</p>
                <CodeBlock title="risk_factors" content={JSON.stringify(finding.risk_factors, null, 2)} language="json" />
              </div>
            )}
          </div>
        )}

        {/* ── Remediation tab ───────────────────────────────────────────────── */}
        {activeTab === "remediation" && (
          <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="space-y-4">
              <div className="rounded-2xl border border-[#a8ff3e]/10 bg-[#a8ff3e]/4 p-5">
                <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/60 mb-3">Remediation guidance</p>
                {finding.remediation ? (
                  <p className="text-sm leading-7 text-white/70" style={{ fontFamily: "var(--font-serif)" }}>{finding.remediation}</p>
                ) : (
                  <p className="font-mono text-xs text-white/30">No remediation guidance recorded for this finding.</p>
                )}
              </div>

              {/* Generic guidance based on severity */}
              <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
                <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50 mb-3">SLA guidance</p>
                <div className="space-y-2">
                  {[
                    { rating: "critical", sla: "24 hours", note: "Immediate escalation required" },
                    { rating: "high", sla: "7 days", note: "Priority remediation" },
                    { rating: "medium", sla: "30 days", note: "Standard sprint cycle" },
                    { rating: "low", sla: "90 days", note: "Backlog acceptable" },
                  ].map(row => (
                    <div key={row.rating}
                      className={`flex items-center justify-between rounded-lg border px-3 py-2 ${finding.risk_rating === row.rating ? "border-[#a8ff3e]/20 bg-[#a8ff3e]/6" : "border-white/5 opacity-30"}`}>
                      <div className="flex items-center gap-2">
                        {finding.risk_rating === row.rating && <div className="h-1.5 w-1.5 rounded-full bg-[#a8ff3e]" />}
                        <span className="font-mono text-xs capitalize text-white/60">{row.rating}</span>
                      </div>
                      <div className="text-right">
                        <p className="font-mono text-xs font-semibold text-white">{row.sla}</p>
                        <p className="font-mono text-[9px] text-white/30">{row.note}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
                <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50 mb-3">Retest</p>
                <p className="font-mono text-xs text-white/40 mb-4">After applying a fix, trigger a targeted retest scan to verify the remediation.</p>
                {scan && (
                  <Link href={`/scans?retest=${scan.id}&finding=${id}`}
                    className="block w-full rounded-xl bg-[#a8ff3e] px-4 py-3 text-center font-mono text-xs font-bold text-[#040a06] transition hover:bg-[#bfff61]">
                    Schedule retest scan
                  </Link>
                )}
                <Link href="/reports" className="mt-2 block w-full rounded-xl border border-white/8 bg-white/4 px-4 py-3 text-center font-mono text-xs text-white/45 transition hover:bg-white/8">
                  Export this finding
                </Link>
              </div>
            </div>
          </div>
        )}

        {/* ── History tab ───────────────────────────────────────────────────── */}
        {activeTab === "history" && (
          <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
            <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/50 mb-5">Status history</p>
            <div className="space-y-4 pl-2">
              <StatusHistoryItem status="open" label="Finding discovered" timestamp={new Date(finding.created_at).toLocaleString()} active={true} />
              <StatusHistoryItem status="triaged" label="Triaged" timestamp={finding.status === "triaged" || finding.status === "resolved" || finding.status === "ignored" ? "Timestamp not yet tracked" : undefined} active={finding.status !== "open"} />
              <StatusHistoryItem status="resolved" label="Resolved / ignored" active={finding.status === "resolved" || finding.status === "ignored"} />
            </div>

            <div className="mt-6 rounded-xl border border-white/7 bg-[#05090f] p-4">
              <p className="mb-3 font-mono text-[10px] text-white/30 uppercase tracking-wider">Add comment</p>
              <textarea value={commentText} onChange={e => setCommentText(e.target.value)} rows={3} placeholder="Add a note, rationale, or suppression reason..." className="field w-full resize-none" />
              <GreenButton isLoading={isSubmitting} disabled={isSubmitting || !commentText.trim()} onClick={submitComment} className="mt-2">Save comment</GreenButton>
            </div>
          </div>
        )}

      </div>
    </main>
  );
}