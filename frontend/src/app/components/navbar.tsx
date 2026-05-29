"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useAuth } from "../lib/auth-context";

const NAV_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/targets", label: "Targets" },
  { href: "/scans", label: "Scans" },
  { href: "/findings", label: "Findings" },
  { href: "/reports", label: "Reports" },
  { href: "/audit", label: "Audit" },
];

export default function Navbar() {
  const pathname = usePathname();
  const { token, clearToken } = useAuth();
  const isLanding = pathname === "/";
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      <nav className="fixed top-0 left-0 right-0 z-40 border-b border-white/6 bg-[#04080f]/95 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between px-4 py-3 sm:px-6">

          {/* Logo */}
          <Link href="/" className="group flex items-center gap-2.5" onClick={() => setMobileOpen(false)}>
            <div className="relative h-6 w-6 flex-shrink-0">
              <div className="absolute inset-0 rounded-sm bg-[#a8ff3e] opacity-20 transition group-hover:opacity-40" />
              <div className="absolute inset-[2px] rounded-sm border border-[#a8ff3e]/60" />
              <div className="absolute inset-[4px] rounded-sm bg-[#a8ff3e]" />
            </div>
            <span className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-white/85">ArmorScan</span>
          </Link>

          {/* Desktop nav — only when logged in and not on landing */}
          {!isLanding && token && (
            <div className="hidden items-center gap-0.5 md:flex">
              {NAV_LINKS.map(({ href, label }) => {
                // active = exact match OR starts with href (for detail pages)
                const active = pathname === href || (pathname.startsWith(href + "/") && href !== "/");
                return (
                  <Link key={href} href={href}
                    className={`rounded-lg px-3 py-2 font-mono text-[11px] uppercase tracking-widest transition ${
                      active ? "bg-[#a8ff3e]/10 text-[#a8ff3e]" : "text-white/40 hover:bg-white/5 hover:text-white/75"
                    }`}>
                    {label}
                  </Link>
                );
              })}
            </div>
          )}

          {/* Right side */}
          <div className="flex items-center gap-2">
            {token ? (
              <>
                <div className="hidden items-center gap-1.5 md:flex">
                  <div className="h-1.5 w-1.5 rounded-full bg-[#a8ff3e] shadow-[0_0_5px_#a8ff3e]" />
                  <span className="font-mono text-[10px] text-white/35">connected</span>
                </div>
                <button onClick={clearToken}
                  className="rounded-lg border border-white/8 px-3 py-1.5 font-mono text-[11px] text-white/40 transition hover:border-white/18 hover:text-white/65">
                  sign out
                </button>
                {/* Mobile hamburger */}
                {!isLanding && (
                  <button onClick={() => setMobileOpen(o => !o)}
                    className="flex h-8 w-8 flex-col items-center justify-center gap-1.5 rounded-lg border border-white/8 md:hidden">
                    <div className={`h-px w-4 bg-white/60 transition-all ${mobileOpen ? "translate-y-[3px] rotate-45" : ""}`} />
                    <div className={`h-px w-4 bg-white/60 transition-all ${mobileOpen ? "opacity-0" : ""}`} />
                    <div className={`h-px w-4 bg-white/60 transition-all ${mobileOpen ? "-translate-y-[3px] -rotate-45" : ""}`} />
                  </button>
                )}
              </>
            ) : (
              <Link href="/login"
                className="rounded-lg bg-[#a8ff3e] px-4 py-2 font-mono text-xs font-bold text-[#040a06] transition hover:bg-[#bfff61]">
                sign in →
              </Link>
            )}
          </div>
        </div>
      </nav>

      {/* Mobile drawer */}
      {mobileOpen && !isLanding && token && (
        <div className="fixed inset-0 z-30 pt-14 md:hidden" onClick={() => setMobileOpen(false)}>
          <div className="border-b border-white/8 bg-[#04080f]/98 backdrop-blur-xl px-4 py-3"
            onClick={e => e.stopPropagation()}>
            <div className="space-y-0.5">
              {NAV_LINKS.map(({ href, label }) => {
                const active = pathname === href || pathname.startsWith(href + "/");
                return (
                  <Link key={href} href={href} onClick={() => setMobileOpen(false)}
                    className={`flex items-center rounded-xl px-4 py-3 font-mono text-sm transition ${
                      active ? "bg-[#a8ff3e]/10 text-[#a8ff3e]" : "text-white/50 hover:bg-white/5 hover:text-white/80"
                    }`}>
                    {label}
                    {active && <span className="ml-auto font-mono text-[10px] text-[#a8ff3e]/50">◆</span>}
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </>
  );
}