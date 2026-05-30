export default function ScanDetailLoading() {
  return (
    <main className="min-h-screen bg-[#04080f] px-3 py-4 sm:px-6">
      <div className="mx-auto max-w-[1500px] space-y-4 sm:space-y-5">
        <header className="rounded-2xl border border-white/7 bg-[#080f18] p-4 sm:p-6">
          <div className="h-3 w-16 animate-pulse rounded bg-white/10" />
          <div className="mt-3 h-7 w-64 animate-pulse rounded bg-white/8" />
          <div className="mt-3 flex gap-2">
            <div className="h-6 w-20 animate-pulse rounded-full bg-white/6" />
            <div className="h-6 w-20 animate-pulse rounded-full bg-white/6" />
          </div>
        </header>
        <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
          <div className="h-80 rounded-2xl border border-white/7 bg-[#080f18] animate-pulse" />
          <div className="h-80 rounded-2xl border border-white/7 bg-[#080f18] animate-pulse" />
        </div>
        <div className="h-64 rounded-2xl border border-white/7 bg-[#080f18] animate-pulse" />
      </div>
    </main>
  );
}
