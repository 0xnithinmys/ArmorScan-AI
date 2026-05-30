export default function FindingsLoading() {
  return (
    <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-[1400px] space-y-5">
        <header className="rounded-2xl border border-white/7 bg-[#080f18] p-6">
          <div className="h-2.5 w-20 animate-pulse rounded bg-[#a8ff3e]/10" />
          <div className="mt-3 h-7 w-36 animate-pulse rounded bg-white/8" />
          <div className="mt-2 h-3 w-72 animate-pulse rounded bg-white/5" />
          <div className="mt-4 flex gap-2">
            <div className="h-7 w-24 animate-pulse rounded-full bg-[#5f1919]/40" />
            <div className="h-7 w-20 animate-pulse rounded-full bg-[#5e3512]/40" />
            <div className="h-7 w-20 animate-pulse rounded-full bg-white/6" />
          </div>
        </header>
        <div className="flex gap-3">
          <div className="h-10 w-52 animate-pulse rounded-xl bg-[#080f18]" />
          <div className="h-10 w-40 animate-pulse rounded-xl bg-[#080f18]" />
        </div>
        <div className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
          <div className="space-y-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-28 rounded-xl border border-white/7 bg-[#05090f] animate-pulse" />
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
