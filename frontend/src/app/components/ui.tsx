"use client";

import { ReactNode } from "react";
import { statusStyle, severityStyle } from "../lib/api";

export function Panel({
  title,
  eyebrow,
  children,
  className = "",
}: {
  title: string;
  eyebrow: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-2xl border border-white/8 bg-[#080f18] p-5 ${className}`}
    >
      <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#a8ff3e]/70">
        {eyebrow}
      </p>
      <h3 className="mt-2 font-mono text-xl font-semibold text-white">{title}</h3>
      <div className="mt-5">{children}</div>
    </section>
  );
}

export function EmptyState({ text }: { text: string }) {
  return (
    <div className="rounded-xl border border-dashed border-white/10 bg-[#05090f] px-6 py-8 text-center font-mono text-xs text-white/30">
      <div className="mb-2 text-[#a8ff3e]/30">[ EMPTY ]</div>
      {text}
    </div>
  );
}

export function StatusBadge({ value }: { value: string }) {
  return (
    <span
      className={`rounded-full border border-white/10 px-3 py-1 font-mono text-[11px] uppercase tracking-wider ${statusStyle(value)}`}
    >
      {value}
    </span>
  );
}

export function SeverityBadge({
  rating,
  score,
}: {
  rating: string;
  score?: number;
}) {
  return (
    <span
      className={`rounded-full border px-3 py-1 font-mono text-[11px] font-semibold uppercase tracking-wider ${severityStyle(rating)}`}
    >
      {rating}
      {score !== undefined ? ` · ${score}/100` : ""}
    </span>
  );
}

export function FieldInput({
  placeholder,
  value,
  onChange,
  type = "text",
  className = "",
}: {
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  className?: string;
}) {
  return (
    <input
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`w-full rounded-xl border border-white/10 bg-[#05090f] px-4 py-3 font-mono text-sm text-white/90 placeholder-white/25 outline-none transition focus:border-[#a8ff3e]/50 focus:ring-1 focus:ring-[#a8ff3e]/20 ${className}`}
    />
  );
}

export function FieldSelect({
  value,
  onChange,
  children,
  className = "",
}: {
  value: string;
  onChange: (v: string) => void;
  children: ReactNode;
  className?: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`w-full rounded-xl border border-white/10 bg-[#05090f] px-4 py-3 font-mono text-sm text-white/90 outline-none transition focus:border-[#a8ff3e]/50 ${className}`}
    >
      {children}
    </select>
  );
}

export function GreenButton({
  children,
  disabled,
  onClick,
  type = "button",
  className = "",
  isLoading = false,
}: {
  children: ReactNode;
  disabled?: boolean;
  onClick?: () => void;
  type?: "button" | "submit" | "reset";
  className?: string;
  isLoading?: boolean;
}) {
  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      onClick={onClick}
      className={`relative flex items-center justify-center gap-2 rounded-xl bg-[#a8ff3e] px-5 py-3 font-mono text-sm font-bold text-[#040a06] transition hover:bg-[#bfff61] active:scale-95 disabled:cursor-not-allowed disabled:opacity-40 ${className}`}
    >
      {isLoading ? (
        <>
          <svg className="h-4 w-4 animate-spin text-[#040a06]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
          <span className="opacity-70">Loading...</span>
        </>
      ) : (
        children
      )}
    </button>
  );
}

export function GhostButton({
  children,
  disabled,
  onClick,
  className = "",
  isLoading = false,
}: {
  children: ReactNode;
  disabled?: boolean;
  onClick?: () => void;
  className?: string;
  isLoading?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled || isLoading}
      onClick={onClick}
      className={`relative flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/4 px-4 py-2 font-mono text-xs text-white/60 transition hover:border-white/20 hover:bg-white/8 hover:text-white/80 disabled:opacity-40 ${className}`}
    >
      {isLoading ? (
        <>
          <svg className="h-3 w-3 animate-spin text-white/60" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
          <span className="opacity-70">Loading...</span>
        </>
      ) : (
        children
      )}
    </button>
  );
}

export function ScanlineOverlay() {
  return (
    <div
      className="pointer-events-none fixed inset-0 z-50 opacity-[0.025]"
      style={{
        backgroundImage:
          "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,255,255,0.5) 2px, rgba(255,255,255,0.5) 3px)",
        backgroundSize: "100% 3px",
      }}
    />
  );
}

export function LoadingState({ text = "Loading data..." }: { text?: string }) {
  return (
    <div className="rounded-xl border border-white/8 bg-[#05090f] px-6 py-8">
      <div className="flex items-center justify-center gap-3">
        <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-[#a8ff3e]" />
        <p className="font-mono text-xs text-white/40">{text}</p>
      </div>
      <div className="mx-auto mt-5 max-w-md space-y-2">
        <div className="h-2 animate-pulse rounded bg-white/8" />
        <div className="h-2 w-3/4 animate-pulse rounded bg-white/6" />
      </div>
    </div>
  );
}

export function PageLoader({ text = "Loading workspace..." }: { text?: string }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#04080f] px-4">
      <div className="w-full max-w-md rounded-2xl border border-white/8 bg-[#080f18] p-6 text-center">
        <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-white/10 border-t-[#a8ff3e]" />
        <p className="mt-4 font-mono text-sm text-white/45">{text}</p>
      </div>
    </main>
  );
}