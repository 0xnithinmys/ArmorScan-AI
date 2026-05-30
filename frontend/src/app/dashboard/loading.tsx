export default function DashboardLoading() {
  return (
    <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-[1600px] space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <div className="h-3 w-32 animate-pulse rounded bg-[#a8ff3e]/10" />
            <div className="h-7 w-48 animate-pulse rounded bg-white/8" />
          </div>
          <div className="h-10 w-28 animate-pulse rounded-xl bg-white/6" />
        </div>
        {/* 4 stat cards */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-2xl border border-white/7 bg-[#080f18] p-5">
              <div className="h-2.5 w-16 animate-pulse rounded bg-white/8" />
              <div className="mt-3 h-9 w-14 animate-pulse rounded bg-white/10" />
              <div className="mt-2 h-2 w-28 animate-pulse rounded bg-white/6" />
            </div>
          ))}
        </div>
        {/* 3 content panels */}
        <div className="grid gap-4 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-56 rounded-2xl border border-white/7 bg-[#080f18] animate-pulse" />
          ))}
        </div>
        {/* 2 panels row */}
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="h-64 rounded-2xl border border-white/7 bg-[#080f18] animate-pulse" />
          <div className="h-64 rounded-2xl border border-white/7 bg-[#080f18] animate-pulse" />
        </div>
      </div>
    </main>
  );
}
