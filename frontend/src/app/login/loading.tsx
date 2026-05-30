export default function LoginLoading() {
  return (
    <main className="flex min-h-[calc(100vh-56px)] items-center justify-center bg-[#04080f] px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="h-7 w-7 animate-pulse rounded-sm bg-[#a8ff3e]/20" />
          <div className="h-4 w-28 animate-pulse rounded bg-white/8" />
        </div>
        <div className="rounded-2xl border border-white/8 bg-[#080f18] p-6">
          <div className="mb-5 h-10 animate-pulse rounded-xl bg-white/6" />
          <div className="space-y-3">
            <div className="h-11 animate-pulse rounded-xl bg-white/5" />
            <div className="h-11 animate-pulse rounded-xl bg-white/5" />
          </div>
          <div className="mt-4 h-11 animate-pulse rounded-xl bg-[#a8ff3e]/20" />
        </div>
      </div>
    </main>
  );
}
