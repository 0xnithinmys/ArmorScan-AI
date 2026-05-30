export default function FindingDetailLoading() {
  return (
    <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-[1400px] space-y-5">
        <header className="rounded-2xl border border-white/7 bg-[#080f18] p-6">
          <div className="h-3 w-16 animate-pulse rounded bg-white/10" />
          <div className="mt-3 h-7 w-72 animate-pulse rounded bg-white/8" />
          <div className="mt-3 flex gap-2">
            <div className="h-6 w-24 animate-pulse rounded-full bg-white/6" />
            <div className="h-6 w-20 animate-pulse rounded-full bg-white/6" />
            <div className="h-6 w-16 animate-pulse rounded-full bg-white/6" />
          </div>
        </header>
        <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
          <div className="space-y-4">
            <div className="h-40 rounded-2xl border border-white/7 bg-[#080f18] animate-pulse" />
            <div className="h-32 rounded-2xl border border-white/7 bg-[#080f18] animate-pulse" />
          </div>
          <div className="h-64 rounded-2xl border border-white/7 bg-[#080f18] animate-pulse" />
        </div>
      </div>
    </main>
  );
}
