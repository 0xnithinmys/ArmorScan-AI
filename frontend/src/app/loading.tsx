export default function Loading() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#04080f]">
      <div className="text-center">
        <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-white/10 border-t-[#a8ff3e]" />
        <p className="mt-4 font-mono text-xs text-white/30">Loading...</p>
      </div>
    </main>
  );
}
