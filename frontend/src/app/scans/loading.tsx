export default function ScansLoading() {
  return (
    <main className="min-h-screen bg-[#04080f] px-3 py-4 sm:px-6">
      <div className="mx-auto max-w-[1400px] space-y-4 sm:space-y-5">
        <header className="rounded-2xl border border-white/7 bg-[#080f18] p-4 sm:p-6">
          <div className="h-2.5 w-20 animate-pulse rounded bg-[#a8ff3e]/10" />
          <div className="mt-3 h-7 w-44 animate-pulse rounded bg-white/8" />
          <div className="mt-2 h-3 w-72 animate-pulse rounded bg-white/5" />
        </header>
        <div className="grid gap-4 sm:gap-5 md:grid-cols-[280px_1fr] lg:grid-cols-[380px_1fr]">
          <div className="h-96 rounded-2xl border border-white/7 bg-[#080f18] animate-pulse" />
          <div className="space-y-4">
            <div className="h-64 rounded-2xl border border-white/7 bg-[#080f18] animate-pulse" />
            <div className="h-48 rounded-2xl border border-white/7 bg-[#080f18] animate-pulse" />
          </div>
        </div>
      </div>
    </main>
  );
}
