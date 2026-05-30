import Link from "next/link";
import { TerminalBlock } from "./components/terminal-block";
 
const FEATURES = [
  {
    href: "/targets",
    tag: "01 / TARGETS",
    title: "Target Registry",
    desc: "Register URLs, APIs, and GitHub repos. Enforce authorization attestation before any scan is permitted by policy.",
    accent: "#a8ff3e",
    icon: "⬡",
  },
  {
    href: "/scans",
    tag: "02 / SCANS",
    title: "Governed Scans",
    desc: "Launch AI-driven vulnerability scans with ArmorIQ intent signing, Celery workers, and live status propagation.",
    accent: "#a8ff3e",
    icon: "◈",
  },
  {
    href: "/findings",
    tag: "03 / FINDINGS",
    title: "Risk Triage",
    desc: "Browse risk-ranked findings with severity scoring, business impact analysis, and one-click status updates.",
    accent: "#a8ff3e",
    icon: "◎",
  },
  {
    href: "/reports",
    tag: "04 / REPORTS",
    title: "Export Suite",
    desc: "Generate SARIF, JSON, Markdown, and PDF reports. Feed directly into CI/CD pipelines and compliance systems.",
    accent: "#a8ff3e",
    icon: "◫",
  },
  {
    href: "/audit",
    tag: "05 / AUDIT",
    title: "Policy Ledger",
    desc: "Every enforcement decision logged immutably. ArmorIQ signed intent plans with full agent trace inspection.",
    accent: "#a8ff3e",
    icon: "◩",
  },
  {
    href: "/dashboard",
    tag: "06 / DASHBOARD",
    title: "Control Plane",
    desc: "Unified cockpit: auth, targets, scans, findings, and policy events — all wired to the FastAPI backend.",
    accent: "#a8ff3e",
    icon: "▣",
  },
];
 
const STATS = [
  { value: "100%", label: "API-wired" },
  { value: "4", label: "export formats" },
  { value: "∞", label: "scan depth" },
  { value: "0", label: "static mocks" },
];
 
function GridBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {/* Radial gradient blobs */}
      <div className="absolute -top-40 left-1/4 h-[500px] w-[500px] rounded-full bg-[#a8ff3e]/6 blur-[120px]" />
      <div className="absolute top-1/3 right-0 h-[400px] w-[400px] rounded-full bg-[#3eaaff]/5 blur-[100px]" />
      <div className="absolute bottom-0 left-0 h-[350px] w-[350px] rounded-full bg-[#a8ff3e]/4 blur-[90px]" />
 
      {/* Fine grid */}
      <div
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(168,255,62,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(168,255,62,0.5) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />
 
      {/* Corner brackets */}
      <div className="absolute top-24 left-8 h-8 w-8 border-l-2 border-t-2 border-[#a8ff3e]/20" />
      <div className="absolute top-24 right-8 h-8 w-8 border-r-2 border-t-2 border-[#a8ff3e]/20" />
      <div className="absolute bottom-8 left-8 h-8 w-8 border-b-2 border-l-2 border-[#a8ff3e]/20" />
      <div className="absolute bottom-8 right-8 h-8 w-8 border-b-2 border-r-2 border-[#a8ff3e]/20" />
    </div>
  );
}
 
export default function LandingPage() {
  return (
    <main className="relative min-h-screen overflow-x-hidden bg-[#04080f]">
      {/* ── HERO ─────────────────────────────────────────── */}
      <section className="relative flex min-h-[calc(100vh-56px)] flex-col items-center justify-center px-6 py-20 text-center">
        <GridBackground />
 
        <div className="relative z-10 w-full max-w-5xl">
          {/* Status pill */}
          <div className="animate-fade-up mb-8 inline-flex items-center gap-2 rounded-full border border-[#a8ff3e]/20 bg-[#a8ff3e]/6 px-4 py-2">
            <span className="h-2 w-2 rounded-full bg-[#a8ff3e] shadow-[0_0_8px_#a8ff3e] animate-pulse" />
            <span className="font-mono text-xs uppercase tracking-[0.3em] text-[#a8ff3e]/80">
              System operational
            </span>
          </div>
 
          {/* Main headline */}
          <h1 className="animate-fade-up delay-100 mb-6 font-mono text-5xl font-bold leading-[1.05] tracking-tight text-white sm:text-7xl lg:text-8xl">
            Autonomous
            <br />
            <span className="text-[#a8ff3e]">security</span>
            <br />
            intelligence.
          </h1>
 
          <p
            className="animate-fade-up delay-200 mx-auto mb-10 max-w-2xl font-serif text-lg italic leading-relaxed text-white/50"
            style={{ fontFamily: "var(--font-serif)" }}
          >
            ArmorScan deploys AI agents to discover, rank, and remediate
            vulnerabilities — governed by ArmorIQ policy signing at every step.
          </p>
 
          {/* CTA row */}
          <div className="animate-fade-up delay-300 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              href="/login"
              className="group relative overflow-hidden rounded-xl bg-[#a8ff3e] px-8 py-4 font-mono text-sm font-bold text-[#040a06] transition hover:bg-[#bfff61] active:scale-95"
            >
              <span className="relative z-10">Launch cockpit →</span>
            </Link>
            <Link
              href="/scans"
              className="rounded-xl border border-white/10 bg-white/4 px-8 py-4 font-mono text-sm text-white/60 transition hover:border-white/20 hover:bg-white/8 hover:text-white/90"
            >
              Start a scan
            </Link>
          </div>
 
          {/* Terminal block (client component) */}
          <TerminalBlock />
        </div>
      </section>
 
      {/* ── STATS BAND ────────────────────────────────────── */}
      <section className="border-y border-white/6 bg-[#080f18] px-6 py-8">
        <div className="mx-auto flex max-w-4xl items-center justify-around gap-6">
          {STATS.map((stat) => (
            <div key={stat.label} className="text-center">
              <p className="font-mono text-3xl font-bold text-[#a8ff3e] sm:text-4xl">
                {stat.value}
              </p>
              <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.3em] text-white/35">
                {stat.label}
              </p>
            </div>
          ))}
        </div>
      </section>
 
      {/* ── FEATURES GRID ─────────────────────────────────── */}
      <section className="px-6 py-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-14 max-w-xl">
            <p className="font-mono text-[10px] uppercase tracking-[0.4em] text-[#a8ff3e]/60">
              Platform surface
            </p>
            <h2 className="mt-3 font-mono text-4xl font-bold text-white">
              Every surface,
              <br />
              <span className="text-white/35">fully wired.</span>
            </h2>
          </div>
 
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature) => (
              <Link
                key={feature.href}
                href={feature.href}
                className="group relative overflow-hidden rounded-2xl border border-white/7 bg-[#080f18] p-6 transition duration-300 hover:border-[#a8ff3e]/25 hover:bg-[#0c1521]"
              >
                {/* Hover glow */}
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(168,255,62,0.06),transparent_60%)] opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
 
                <div className="relative">
                  <div className="mb-5 flex items-center justify-between">
                    <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-white/25">
                      {feature.tag}
                    </span>
                    <span className="font-mono text-2xl text-[#a8ff3e]/40 transition group-hover:text-[#a8ff3e]/80">
                      {feature.icon}
                    </span>
                  </div>
                  <h3 className="mb-3 font-mono text-lg font-semibold text-white/90 transition group-hover:text-white">
                    {feature.title}
                  </h3>
                  <p className="text-sm leading-relaxed text-white/40 transition group-hover:text-white/60"
                     style={{ fontFamily: "var(--font-serif)" }}>
                    {feature.desc}
                  </p>
                  <div className="mt-6 flex items-center gap-2">
                    <span className="font-mono text-xs text-[#a8ff3e]/0 transition group-hover:text-[#a8ff3e]/80">
                      open module →
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>
 
      {/* ── HOW IT WORKS ──────────────────────────────────── */}
      <section className="border-t border-white/6 px-6 py-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-14 max-w-xl">
            <p className="font-mono text-[10px] uppercase tracking-[0.4em] text-[#a8ff3e]/60">
              Protocol
            </p>
            <h2 className="mt-3 font-mono text-4xl font-bold text-white">
              How ArmorScan
              <br />
              <span className="text-white/35">operates.</span>
            </h2>
          </div>
 
          <div className="grid gap-px bg-white/6 sm:grid-cols-2 lg:grid-cols-4 rounded-2xl overflow-hidden">
            {[
              {
                step: "01",
                title: "Register",
                body: "Add a target URL, API endpoint, or GitHub repo. Attest authorization.",
              },
              {
                step: "02",
                title: "Authorize",
                body: "ArmorIQ signs an intent plan. Policy engine validates scope before the agent touches anything.",
              },
              {
                step: "03",
                title: "Execute",
                body: "Celery workers dispatch AI scan agents. Live status flows back through the FastAPI surface.",
              },
              {
                step: "04",
                title: "Report",
                body: "Risk-ranked findings land in the ledger. Export SARIF, JSON, PDF, or Markdown instantly.",
              },
            ].map((item) => (
              <div
                key={item.step}
                className="flex flex-col justify-between bg-[#080f18] p-6 lg:p-8"
              >
                <div>
                  <span className="font-mono text-[10px] text-[#a8ff3e]/40 uppercase tracking-[0.4em]">
                    {item.step}
                  </span>
                  <h3 className="mt-3 font-mono text-2xl font-bold text-white">
                    {item.title}
                  </h3>
                  <p
                    className="mt-4 text-sm leading-relaxed text-white/45"
                    style={{ fontFamily: "var(--font-serif)" }}
                  >
                    {item.body}
                  </p>
                </div>
                <div className="mt-8 h-px bg-[#a8ff3e]/15" />
              </div>
            ))}
          </div>
        </div>
      </section>
 
      {/* ── CTA FOOTER ────────────────────────────────────── */}
      <section className="border-t border-white/6 px-6 py-24 text-center">
        <div className="mx-auto max-w-2xl">
          <div className="mb-6 font-mono text-[10px] uppercase tracking-[0.4em] text-[#a8ff3e]/50">
            &lt; ready &gt;
          </div>
          <h2 className="mb-6 font-mono text-4xl font-bold leading-tight text-white sm:text-5xl">
            Start scanning
            <br />
            <span className="text-white/30">in under a minute.</span>
          </h2>
          <p
            className="mx-auto mb-10 max-w-lg text-base italic leading-relaxed text-white/40"
            style={{ fontFamily: "var(--font-serif)" }}
          >
            Register, authorize a target, and let ArmorScan's agents do the
            rest. Full audit trail included.
          </p>
          <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              href="/login"
              className="rounded-xl bg-[#a8ff3e] px-10 py-4 font-mono text-sm font-bold text-[#040a06] transition hover:bg-[#bfff61] active:scale-95"
            >
              Open dashboard →
            </Link>
            <Link
              href="/targets"
              className="rounded-xl border border-white/10 bg-white/4 px-10 py-4 font-mono text-sm text-white/55 transition hover:border-white/20 hover:bg-white/8 hover:text-white/85"
            >
              Add a target
            </Link>
          </div>
        </div>
      </section>
 
      {/* Footer line */}
      <footer className="border-t border-white/6 px-6 py-6">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <span className="font-mono text-xs text-white/20">
            ArmorScan AI © 2025
          </span>
          <span className="font-mono text-xs text-white/15">
            FastAPI · Celery · ArmorIQ
          </span>
        </div>
      </footer>
    </main>
  );
}