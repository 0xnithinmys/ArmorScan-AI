"use client";

import { useState, useEffect } from "react";

export function TerminalLine({ text, delay = 0 }: { text: string; delay?: number }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), delay);
    return () => clearTimeout(t);
  }, [delay]);

  return (
    <div
      className={`font-mono text-xs text-[#a8ff3e]/60 transition-opacity duration-300 ${visible ? "opacity-100" : "opacity-0"}`}
    >
      <span className="mr-2 text-[#a8ff3e]/30">{">"}</span>
      {text}
    </div>
  );
}

export function TerminalBlock() {
  return (
    <div className="animate-fade-up delay-500 mx-auto mt-16 w-full max-w-lg rounded-2xl border border-white/8 bg-[#080f18] p-5 text-left shadow-[0_32px_80px_rgba(0,0,0,0.6)]">
      <div className="mb-4 flex items-center gap-2">
        <div className="h-3 w-3 rounded-full bg-[#ff5f57]" />
        <div className="h-3 w-3 rounded-full bg-[#ffbd2e]" />
        <div className="h-3 w-3 rounded-full bg-[#28c840]" />
        <span className="ml-2 font-mono text-xs text-white/20">
          armorscan — agent
        </span>
      </div>
      <div className="space-y-2">
        <TerminalLine text="initializing ArmorIQ policy engine..." delay={800} />
        <TerminalLine text="loading scan worker pool..." delay={1200} />
        <TerminalLine text="connecting to FastAPI surface..." delay={1600} />
        <TerminalLine text="agent ready. awaiting target authorization." delay={2000} />
        <div className="mt-1 flex items-center gap-2 font-mono text-xs text-[#a8ff3e]">
          <span className="text-[#a8ff3e]/40">{">"}</span>
          <span className="text-[#a8ff3e]">_</span>
          <span className="animate-blink text-[#a8ff3e]">█</span>
        </div>
      </div>
    </div>
  );
}
