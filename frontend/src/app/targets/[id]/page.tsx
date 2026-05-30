"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "../../lib/auth-context";
import {
  API_BASE, authHeaders, readError,
  Target, AuthorizationProof,
} from "../../lib/api";
import {
  Panel, EmptyState, StatusBadge, GreenButton, GhostButton,
} from "../../components/ui";

export default function TargetDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { token, isLoaded } = useAuth();
  
  const [target, setTarget] = useState<Target | null>(null);
  const [proofs, setProofs] = useState<AuthorizationProof[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  
  const [selectedProofType, setSelectedProofType] = useState("dns_txt");
  const [verifyProofValue, setVerifyProofValue] = useState("");
  const [issuing, setIssuing] = useState(false);
  const [verifying, setVerifying] = useState(false);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/targets/${id}`, {
        headers: authHeaders(token),
      });
      if (!res.ok) throw new Error(await readError(res));
      const data = await res.json();
      setTarget(data);
      
      const proofsRes = await fetch(`${API_BASE}/targets/${id}/proofs`, {
        headers: authHeaders(token),
      });
      if (proofsRes.ok) {
        setProofs(await proofsRes.json());
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load target");
    }
  }, [id, token]);

  useEffect(() => { if (!isLoaded) return; load().catch(e => setError(e.message)); }, [load, isLoaded]);

  async function issueChallenge() {
    setIssuing(true); setError(""); setMessage("");
    try {
      const res = await fetch(`${API_BASE}/targets/${id}/proofs/challenge`, {
        method: "POST",
        headers: { ...authHeaders(token), "Content-Type": "application/json" },
        body: JSON.stringify({ proof_type: selectedProofType }),
      });
      if (!res.ok) throw new Error(await readError(res));
      await load();
      setMessage("Challenge issued. Follow the instructions to verify.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to issue challenge");
    } finally {
      setIssuing(false);
    }
  }

  async function verifyProof(proofType: string, challengeToken: string) {
    setVerifying(true); setError(""); setMessage("");
    try {
      const res = await fetch(`${API_BASE}/targets/${id}/authorize`, {
        method: "POST",
        headers: { ...authHeaders(token), "Content-Type": "application/json" },
        body: JSON.stringify({ 
          proof_type: proofType,
          proof: verifyProofValue || undefined,
          challenge_token: challengeToken
        }),
      });
      if (!res.ok) throw new Error(await readError(res));
      await load();
      setMessage("Verification successful! Target is now verified.");
      setVerifyProofValue("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Verification failed");
      await load(); // Reload to get updated proof status
    } finally {
      setVerifying(false);
    }
  }

  if (!target) {
    return (
      <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6 flex items-center justify-center">
        <p className="font-mono text-white/50">{error ? error : "Loading..."}</p>
      </main>
    );
  }

  const isVerified = target.authorization_status === "verified";
  
  // Find the most recent pending proof of the selected type
  const activeProof = proofs.find(p => p.proof_type === selectedProofType && p.status === "pending");

  return (
    <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-[1000px] space-y-5">
        
        {/* Header */}
        <header className="rounded-2xl border border-white/7 bg-[#080f18] p-6 relative overflow-hidden">
          {isVerified && (
            <div className="absolute inset-0 pointer-events-none border-2 border-[#a8ff3e]/20 rounded-2xl" />
          )}
          <Link href="/targets" className="font-mono text-[10px] uppercase tracking-[0.4em] text-white/40 hover:text-white transition">
            ← Back to Targets
          </Link>
          <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h1 className="font-mono text-3xl font-bold text-white flex items-center gap-3">
                {target.name}
              </h1>
              <p className="mt-2 font-mono text-sm text-white/60">{target.target_url}</p>
              <div className="mt-4 flex items-center gap-3">
                <StatusBadge value={target.authorization_status} />
                <span className="rounded-full border border-white/8 bg-white/4 px-2 py-0.5 font-mono text-[10px] uppercase text-white/35">
                  {target.target_type}
                </span>
              </div>
            </div>
            
            <div className="flex gap-2">
              <GreenButton 
                disabled={!isVerified} 
                onClick={() => router.push("/scans")}
                className={!isVerified ? "opacity-50" : ""}
              >
                Create Scan
              </GreenButton>
            </div>
          </div>
          
          {(message || error) && (
            <div className="mt-6 space-y-2">
              {message && <p className="rounded-xl border border-[#a8ff3e]/15 bg-[#a8ff3e]/6 px-4 py-3 font-mono text-xs text-[#a8ff3e]/80">{message}</p>}
              {error && <p className="rounded-xl border border-[#ff7c70]/20 bg-[#ff7c70]/6 px-4 py-3 font-mono text-xs text-[#ffb3ad]">{error}</p>}
            </div>
          )}
        </header>

        {/* Authorization Flow */}
        <Panel title="Target Authorization" eyebrow="REQUIRED FOR SCANNING">
          {isVerified ? (
            <div className="rounded-xl border border-[#a8ff3e]/20 bg-[#a8ff3e]/5 p-6 text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[#a8ff3e]/20 text-[#a8ff3e]">
                ✓
              </div>
              <h3 className="font-mono text-lg font-semibold text-white">Target Verified</h3>
              <p className="mt-2 font-mono text-sm text-white/60">
                This target has been successfully verified via {target.authorization_proof_type}. It is now eligible for active security scanning.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="rounded-xl border border-[#ffb15f]/20 bg-[#ffb15f]/5 p-4">
                <p className="font-mono text-xs leading-5 text-[#ffd8ad]">
                  <strong className="text-[#ffb15f]">Warning:</strong> This target cannot be scanned until ownership is verified. Choose a verification method below to prove you control this target.
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-[200px_1fr]">
                <div className="flex flex-col gap-2 min-w-0">
                  {[
                    { id: "dns_txt", label: "DNS TXT Record" },
                    { id: "http_file", label: "HTTP File" },
                    { id: "meta_tag", label: "HTML Meta Tag" },
                    { id: "github_file", label: "GitHub Repo File" }
                  ].map(method => (
                    <button
                      key={method.id}
                      onClick={() => { setSelectedProofType(method.id); setError(""); setMessage(""); }}
                      className={`text-left rounded-xl border px-4 py-3 font-mono text-xs transition ${
                        selectedProofType === method.id 
                          ? "border-[#a8ff3e]/50 bg-[#a8ff3e]/10 text-[#a8ff3e]" 
                          : "border-white/10 bg-[#05090f] text-white/60 hover:bg-white/5"
                      }`}
                    >
                      {method.label}
                    </button>
                  ))}
                </div>

                <div className="rounded-xl border border-white/10 bg-[#05090f] p-5 min-w-0">
                  {!activeProof ? (
                    <div className="space-y-4">
                      <p className="font-mono text-sm text-white/80">
                        Issue a challenge to start the {selectedProofType.replace("_", " ").toUpperCase()} verification process.
                      </p>
                      <GreenButton onClick={issueChallenge} disabled={issuing}>
                        {issuing ? "Issuing..." : "Issue Challenge"}
                      </GreenButton>
                    </div>
                  ) : (
                    <div className="space-y-5">
                      <div>
                        <h4 className="font-mono text-[10px] uppercase tracking-wider text-[#a8ff3e]/70">Instructions</h4>
                        <p className="mt-2 font-mono text-sm leading-relaxed text-white/80">{activeProof.instructions}</p>
                      </div>
                      
                      <div className="rounded-lg border border-white/10 bg-[#0a0e1a] p-4">
                        <h4 className="font-mono text-[10px] uppercase tracking-wider text-white/40">Expected Value</h4>
                        <code className="mt-2 block break-all font-mono text-sm text-[#a8ff3e]">{activeProof.expected_value}</code>
                      </div>

                      {selectedProofType === "github_file" && (
                        <div>
                          <label className="block font-mono text-xs text-white/60 mb-2">Provide the raw GitHub file URL:</label>
                          <input 
                            className="w-full rounded-xl border border-white/10 bg-[#0a0e1a] px-4 py-3 font-mono text-sm text-white placeholder-white/30 outline-none focus:border-[#a8ff3e]/50"
                            placeholder="https://raw.githubusercontent.com/..."
                            value={verifyProofValue}
                            onChange={e => setVerifyProofValue(e.target.value)}
                          />
                        </div>
                      )}

                      <div className="flex gap-3">
                        <GreenButton 
                          onClick={() => verifyProof(activeProof.proof_type, activeProof.challenge_token)}
                          disabled={verifying || (selectedProofType === "github_file" && !verifyProofValue)}
                        >
                          {verifying ? "Verifying..." : "Verify Now"}
                        </GreenButton>
                        <GhostButton onClick={issueChallenge} disabled={issuing}>
                          Regenerate Challenge
                        </GhostButton>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </Panel>

        {/* Proofs History */}
        {proofs.length > 0 && (
          <Panel title="Verification History" eyebrow="AUDIT LOG">
            <div className="space-y-3">
              {proofs.map(proof => (
                <div key={proof.id} className="rounded-xl border border-white/7 bg-[#05090f] p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-white/80 uppercase">{proof.proof_type.replace("_", " ")}</span>
                      <StatusBadge value={proof.status} />
                    </div>
                    <p className="mt-2 font-mono text-[10px] text-white/40">
                      Created: {new Date(proof.created_at).toLocaleString()}
                      {proof.verified_at && ` · Verified: ${new Date(proof.verified_at).toLocaleString()}`}
                    </p>
                    {proof.failure_reason && (
                      <p className="mt-2 font-mono text-xs text-[#ffb3ad]">{proof.failure_reason}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        )}
      </div>
    </main>
  );
}
