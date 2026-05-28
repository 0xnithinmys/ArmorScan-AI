"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "../lib/auth-context";
import { API_BASE, readError } from "../lib/api";

export default function LoginPage() {
  const { setToken } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ email: "", password: "", full_name: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      if (mode === "register") {
        const r = await fetch(`${API_BASE}/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        });
        if (!r.ok) throw new Error(await readError(r));
      }
      const fd = new FormData();
      fd.set("username", form.email);
      fd.set("password", form.password);
      const r = await fetch(`${API_BASE}/auth/login`, { method: "POST", body: fd });
      if (!r.ok) throw new Error(await readError(r));
      const body = (await r.json()) as { access_token: string };
      setToken(body.access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-[calc(100vh-56px)] items-center justify-center bg-[#04080f] px-4">
      {/* Background glow */}
      <div className="pointer-events-none fixed inset-0">
        <div className="absolute left-1/2 top-1/3 h-[400px] w-[400px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#a8ff3e]/5 blur-[100px]" />
      </div>

      <div className="relative w-full max-w-sm">
        {/* Logo mark */}
        <div className="mb-8 text-center">
          <Link href="/" className="inline-flex items-center gap-3 group">
            <div className="relative h-7 w-7">
              <div className="absolute inset-0 rounded-sm bg-[#a8ff3e] opacity-20 group-hover:opacity-40 transition" />
              <div className="absolute inset-[2px] rounded-sm border border-[#a8ff3e]/60" />
              <div className="absolute inset-[5px] rounded-sm bg-[#a8ff3e]" />
            </div>
            <span className="font-mono text-sm font-bold tracking-[0.2em] text-white/80 uppercase">ArmorScan</span>
          </Link>
          <p className="mt-3 font-mono text-xs text-white/30">
            {mode === "login" ? "Sign in to your account" : "Create a new account"}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="rounded-2xl border border-white/8 bg-[#080f18] p-6 shadow-[0_32px_80px_rgba(0,0,0,0.5)]">
          {/* Mode toggle */}
          <div className="mb-5 flex gap-1 rounded-xl border border-white/8 p-1">
            {(["login", "register"] as const).map(m => (
              <button key={m} type="button" onClick={() => setMode(m)}
                className={`flex-1 rounded-lg py-2 font-mono text-xs capitalize transition ${mode === m ? "bg-[#a8ff3e] text-[#040a06] font-bold" : "text-white/40 hover:text-white/70"}`}>
                {m}
              </button>
            ))}
          </div>

          <div className="space-y-3">
            {mode === "register" && (
              <input className="field" placeholder="Full name" value={form.full_name}
                onChange={e => setForm({ ...form, full_name: e.target.value })} required />
            )}
            <input className="field" type="email" placeholder="Email" value={form.email}
              onChange={e => setForm({ ...form, email: e.target.value })} required />
            <input className="field" type="password" placeholder="Password" value={form.password}
              onChange={e => setForm({ ...form, password: e.target.value })} required />
          </div>

          {error && (
            <p className="mt-4 rounded-xl border border-[#ff7c70]/20 bg-[#ff7c70]/6 px-4 py-2 font-mono text-xs text-[#ffb3ad]">
              {error}
            </p>
          )}

          <button type="submit" disabled={loading}
            className="mt-4 w-full rounded-xl bg-[#a8ff3e] py-3 font-mono text-sm font-bold text-[#040a06] transition hover:bg-[#bfff61] active:scale-95 disabled:opacity-50">
            {loading ? "..." : mode === "register" ? "Create account" : "Sign in"}
          </button>
        </form>

        <p className="mt-4 text-center font-mono text-xs text-white/25">
          <Link href="/" className="hover:text-white/50 transition">← back to home</Link>
        </p>
      </div>
    </main>
  );
}