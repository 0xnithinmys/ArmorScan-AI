export default function ReportsLoading() {
  return (
    <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-[1400px] space-y-5">
        <header className="rounded-2xl border border-white/7 bg-[#080f18] p-6">
          <div className="h-2.5 w-24 animate-pulse rounded bg-[#a8ff3e]/10" />
          <div className="mt-3 h-7 w-40 animate-pulse rounded bg-white/8" />
          <div className="mt-2 h-3 w-64 animate-pulse rounded bg-white/5" />
        </header>
        <div className="h-96 rounded-2xl border border-white/7 bg-[#080f18] animate-pulse" />
      </div>
    </main>
  );
}
