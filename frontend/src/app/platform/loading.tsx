export default function PlatformLoading() {
  return (
    <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-[1500px] space-y-5">
        <header className="rounded-2xl border border-white/7 bg-[#080f18] p-6">
          <div className="h-2.5 w-20 animate-pulse rounded bg-[#a8ff3e]/10" />
          <div className="mt-3 h-8 w-48 animate-pulse rounded bg-white/8" />
          <div className="mt-2 h-3 w-96 animate-pulse rounded bg-white/5" />
        </header>
        <div className="grid gap-5 xl:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-72 rounded-2xl border border-white/7 bg-[#080f18] animate-pulse" />
          ))}
        </div>
      </div>
    </main>
  );
}
