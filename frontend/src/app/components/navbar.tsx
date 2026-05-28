"use client";
 
import Link from "next/link";
import { usePathname } from "next/navigation";
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
 
  return (
    <nav className="fixed top-0 left-0 right-0 z-40 border-b border-white/6 bg-[#04080f]/90 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1600px] items-center justify-between px-6 py-3">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="relative h-7 w-7">
            <div className="absolute inset-0 rounded-sm bg-[#a8ff3e] opacity-20 group-hover:opacity-40 transition" />
            <div className="absolute inset-[2px] rounded-sm border border-[#a8ff3e]/60" />
            <div className="absolute inset-[5px] rounded-sm bg-[#a8ff3e]" />
          </div>
          <span className="font-mono text-sm font-bold tracking-[0.2em] text-white/90 uppercase">
            ArmorScan
          </span>
        </Link>
 
        {/* Nav links — hidden on landing */}
        {!isLanding && (
          <div className="hidden items-center gap-1 md:flex">
            {NAV_LINKS.map(({ href, label }) => {
              const active = pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={`rounded-lg px-3 py-2 font-mono text-xs uppercase tracking-widest transition ${
                    active
                      ? "bg-[#a8ff3e]/10 text-[#a8ff3e]"
                      : "text-white/45 hover:bg-white/6 hover:text-white/80"
                  }`}
                >
                  {label}
                </Link>
              );
            })}
          </div>
        )}
 
        {/* Right side */}
        <div className="flex items-center gap-3">
          {token ? (
            <>
              <div className="hidden items-center gap-2 md:flex">
                <div className="h-2 w-2 rounded-full bg-[#a8ff3e] shadow-[0_0_6px_#a8ff3e]" />
                <span className="font-mono text-xs text-white/40">connected</span>
              </div>
              <button
                onClick={clearToken}
                className="rounded-lg border border-white/10 px-3 py-2 font-mono text-xs text-white/45 transition hover:border-white/20 hover:text-white/70"
              >
                sign out
              </button>
            </>
          ) : (
            <Link
              href="/login"
              className="rounded-lg bg-[#a8ff3e] px-4 py-2 font-mono text-xs font-bold text-[#040a06] transition hover:bg-[#bfff61]"
            >
              sign in →
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
 