type RouteLoaderProps = {
  title: string;
  subtitle: string;
  variant?: "default" | "detail" | "auth" | "hero";
};

function SkeletonCard({
  className = "",
  lines = 3,
}: {
  className?: string;
  lines?: number;
}) {
  return (
    <div className={`rounded-2xl border border-white/7 bg-[#080f18] p-5 ${className}`}>
      <div className="space-y-3">
        <div className="h-3 w-24 animate-pulse rounded-full bg-white/8" />
        {Array.from({ length: lines }, (_, index) => (
          <div
            key={index}
            className={`h-3 animate-pulse rounded-full bg-white/8 ${
              index === lines - 1 ? "w-3/4" : index === 0 ? "w-full" : "w-5/6"
            }`}
          />
        ))}
      </div>
    </div>
  );
}

export function RouteLoader({
  title,
  subtitle,
  variant = "default",
}: RouteLoaderProps) {
  if (variant === "auth") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#04080f] px-4">
        <div className="w-full max-w-sm rounded-2xl border border-white/8 bg-[#080f18] p-6">
          <div className="h-3 w-28 animate-pulse rounded-full bg-white/8" />
          <div className="mt-4 h-8 w-48 animate-pulse rounded-full bg-white/10" />
          <div className="mt-3 h-4 w-full animate-pulse rounded-full bg-white/8" />
          <div className="mt-6 space-y-3">
            <div className="h-11 animate-pulse rounded-xl bg-white/8" />
            <div className="h-11 animate-pulse rounded-xl bg-white/8" />
            <div className="h-11 animate-pulse rounded-xl bg-white/8" />
          </div>
        </div>
      </main>
    );
  }

  if (variant === "detail") {
    return (
      <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
        <div className="mx-auto max-w-[1400px] space-y-5">
          <div className="rounded-2xl border border-white/7 bg-[#080f18] p-6">
            <div className="h-3 w-28 animate-pulse rounded-full bg-white/8" />
            <div className="mt-3 h-8 w-80 max-w-full animate-pulse rounded-full bg-white/10" />
            <div className="mt-3 h-4 w-full max-w-2xl animate-pulse rounded-full bg-white/8" />
            <div className="mt-6 flex flex-wrap gap-2">
              <div className="h-8 w-24 animate-pulse rounded-full bg-white/8" />
              <div className="h-8 w-24 animate-pulse rounded-full bg-white/8" />
              <div className="h-8 w-24 animate-pulse rounded-full bg-white/8" />
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
            <SkeletonCard className="min-h-[320px]" lines={4} />
            <SkeletonCard className="min-h-[320px]" lines={5} />
          </div>
        </div>
      </main>
    );
  }

  if (variant === "hero") {
    return (
      <main className="min-h-screen bg-[#04080f] px-6 py-16">
        <div className="mx-auto max-w-6xl space-y-6">
          <div className="rounded-3xl border border-white/8 bg-[#080f18] p-8">
            <div className="h-3 w-32 animate-pulse rounded-full bg-white/8" />
            <div className="mt-6 h-16 w-full max-w-3xl animate-pulse rounded-full bg-white/10" />
            <div className="mt-4 h-4 w-full max-w-2xl animate-pulse rounded-full bg-white/8" />
            <div className="mt-8 flex flex-wrap gap-3">
              <div className="h-12 w-40 animate-pulse rounded-xl bg-white/8" />
              <div className="h-12 w-36 animate-pulse rounded-xl bg-white/8" />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <SkeletonCard lines={2} />
            <SkeletonCard lines={2} />
            <SkeletonCard lines={2} />
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#04080f] px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-[1400px] space-y-5">
        <div className="rounded-2xl border border-white/7 bg-[#080f18] p-6">
          <div className="h-3 w-28 animate-pulse rounded-full bg-white/8" />
          <div className="mt-3 h-8 w-72 max-w-full animate-pulse rounded-full bg-white/10" />
          <div className="mt-3 h-4 w-full max-w-xl animate-pulse rounded-full bg-white/8" />
          <p className="sr-only">
            {title}
            {subtitle ? ` ${subtitle}` : ""}
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <SkeletonCard lines={3} />
          <SkeletonCard lines={4} />
          <SkeletonCard lines={3} />
        </div>
      </div>
    </main>
  );
}
