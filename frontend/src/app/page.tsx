const pipelineMetrics = [
  {
    label: "Active scans",
    value: "12",
    detail: "+3 in the last hour",
  },
  {
    label: "Critical findings",
    value: "04",
    detail: "2 need triage now",
  },
  {
    label: "Mean validation",
    value: "93%",
    detail: "AI-confirmed confidence",
  },
  {
    label: "Policies enforced",
    value: "128",
    detail: "0 fail-open events",
  },
];

const scanQueue = [
  {
    name: "prod.customer-portal.app",
    mode: "Dynamic web audit",
    status: "Running",
    progress: 74,
    eta: "11 min",
    risk: "High",
  },
  {
    name: "staging.api-gateway.internal",
    mode: "API misuse sweep",
    status: "Queued",
    progress: 18,
    eta: "23 min",
    risk: "Moderate",
  },
  {
    name: "github.com/acme/payments-ui",
    mode: "Repo code review",
    status: "Reviewing",
    progress: 91,
    eta: "4 min",
    risk: "Critical",
  },
];

const findings = [
  {
    severity: "Critical",
    title: "Reflected XSS on invoice search",
    location: "/billing/invoices?query=",
    confidence: "96%",
    summary: "Payload reflected in DOM after client-side decoding path.",
  },
  {
    severity: "High",
    title: "Potential BOLA on account export endpoint",
    location: "POST /api/v1/accounts/export",
    confidence: "91%",
    summary: "Cross-tenant object IDs accepted without ownership validation.",
  },
  {
    severity: "Medium",
    title: "Leaky stack trace on auth callback",
    location: "/oauth/callback",
    confidence: "88%",
    summary: "Unhandled exception discloses framework and package metadata.",
  },
];

const auditEvents = [
  "ArmorIQ signed intent plan for prod.customer-portal.app",
  "Playwright crawler discovered 43 reachable interactive nodes",
  "Payload verifier blocked one out-of-scope redirect attempt",
  "Report synthesizer generated SARIF and JSON artifacts",
];

const sideNav = [
  "Mission Control",
  "Targets",
  "Live Scans",
  "Findings",
  "Policies",
  "Reports",
  "Audit Trail",
];

function getSeverityStyle(severity: string) {
  switch (severity) {
    case "Critical":
      return "bg-[#5f1919] text-[#ffb3ad] ring-1 ring-[#8d2d2d]";
    case "High":
      return "bg-[#5e3512] text-[#ffd8ad] ring-1 ring-[#8c531f]";
    case "Medium":
      return "bg-[#3f4216] text-[#e9f29f] ring-1 ring-[#646a26]";
    default:
      return "bg-white/10 text-white/80 ring-1 ring-white/10";
  }
}

function getStatusStyle(status: string) {
  switch (status) {
    case "Running":
      return "text-[#9ef3cf]";
    case "Reviewing":
      return "text-[#ffd38f]";
    default:
      return "text-[#b9c4ff]";
  }
}

export default function Home() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(153,209,178,0.18),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(87,129,255,0.14),_transparent_26%),linear-gradient(180deg,_#07111f_0%,_#0b1424_42%,_#09101b_100%)] text-[#f7f4ea]">
      <div className="mx-auto flex min-h-screen max-w-[1600px] gap-6 px-4 py-4 sm:px-6 lg:px-8">
        <aside className="hidden w-[260px] shrink-0 flex-col rounded-[28px] border border-white/10 bg-white/6 p-5 shadow-[0_20px_80px_rgba(0,0,0,0.35)] backdrop-blur md:flex">
          <div className="mb-8">
            <p className="text-xs uppercase tracking-[0.35em] text-[#8db39d]">
              ArmorScan AI
            </p>
            <h1 className="mt-3 text-2xl font-semibold tracking-tight text-white">
              Security audit cockpit
            </h1>
            <p className="mt-3 text-sm leading-6 text-white/65">
              Governed AI scanning for repos, web apps, and APIs with real-time
              policy enforcement.
            </p>
          </div>

          <nav className="space-y-2">
            {sideNav.map((item, index) => (
              <div
                key={item}
                className={`rounded-2xl px-4 py-3 text-sm transition ${
                  index === 0
                    ? "bg-[#d7f266] text-[#102018]"
                    : "text-white/72 hover:bg-white/6 hover:text-white"
                }`}
              >
                {item}
              </div>
            ))}
          </nav>

          <div className="mt-auto rounded-[24px] border border-[#d7f266]/25 bg-[#d7f266]/10 p-4">
            <p className="text-xs uppercase tracking-[0.3em] text-[#d7f266]">
              Safety status
            </p>
            <p className="mt-3 text-sm leading-6 text-white/80">
              All outbound actions are locked behind signed intent tokens and
              fail-closed policy checks.
            </p>
          </div>
        </aside>

        <section className="flex-1">
          <div className="rounded-[32px] border border-white/10 bg-[#08101b]/80 p-5 shadow-[0_24px_80px_rgba(0,0,0,0.35)] backdrop-blur sm:p-7">
            <div className="flex flex-col gap-5 border-b border-white/10 pb-6 lg:flex-row lg:items-end lg:justify-between">
              <div className="max-w-3xl">
                <p className="text-xs uppercase tracking-[0.4em] text-[#8db39d]">
                  Phase 2 dashboard
                </p>
                <h2 className="mt-3 max-w-2xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                  Launch and govern AI-native web security scans from one place.
                </h2>
                <p className="mt-4 max-w-2xl text-sm leading-7 text-white/68 sm:text-base">
                  Intake targets, monitor autonomous execution, review validated
                  findings, and export developer-ready reports without losing
                  policy visibility.
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <button className="rounded-full bg-[#d7f266] px-5 py-3 text-sm font-semibold text-[#122111] transition hover:bg-[#e5fb84]">
                  Start new scan
                </button>
                <button className="rounded-full border border-white/12 bg-white/6 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10">
                  Export latest report
                </button>
              </div>
            </div>

            <div className="mt-6 grid gap-4 xl:grid-cols-[1.25fr_0.9fr]">
              <div className="rounded-[28px] border border-white/10 bg-[linear-gradient(145deg,_rgba(215,242,102,0.14),_rgba(255,255,255,0.03))] p-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-[0.3em] text-[#d7f266]">
                      New mission
                    </p>
                    <h3 className="mt-3 text-2xl font-semibold text-white">
                      Configure a scan target
                    </h3>
                  </div>
                  <div className="rounded-full border border-white/10 px-4 py-2 text-xs uppercase tracking-[0.25em] text-white/60">
                    MVP control plane
                  </div>
                </div>

                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  <label className="block rounded-[24px] border border-white/10 bg-[#07111c] p-4">
                    <span className="text-xs uppercase tracking-[0.25em] text-white/45">
                      Target URL or repo
                    </span>
                    <div className="mt-3 rounded-2xl border border-white/8 bg-white/4 px-4 py-3 text-sm text-white/72">
                      https://prod.customer-portal.app
                    </div>
                  </label>

                  <label className="block rounded-[24px] border border-white/10 bg-[#07111c] p-4">
                    <span className="text-xs uppercase tracking-[0.25em] text-white/45">
                      Scan mode
                    </span>
                    <div className="mt-3 flex flex-wrap gap-2 text-sm">
                      <span className="rounded-full bg-[#d7f266] px-3 py-2 font-medium text-[#132311]">
                        Dynamic web audit
                      </span>
                      <span className="rounded-full border border-white/10 px-3 py-2 text-white/70">
                        Repository review
                      </span>
                      <span className="rounded-full border border-white/10 px-3 py-2 text-white/70">
                        API fuzzing
                      </span>
                    </div>
                  </label>

                  <label className="block rounded-[24px] border border-white/10 bg-[#07111c] p-4">
                    <span className="text-xs uppercase tracking-[0.25em] text-white/45">
                      Scope guardrails
                    </span>
                    <div className="mt-3 space-y-2 text-sm text-white/72">
                      <p>Subdomains: `*.customer-portal.app`</p>
                      <p>Rate limit: `90 req/min`</p>
                      <p>Restricted actions: `file write`, `logout flows`</p>
                    </div>
                  </label>

                  <label className="block rounded-[24px] border border-white/10 bg-[#07111c] p-4">
                    <span className="text-xs uppercase tracking-[0.25em] text-white/45">
                      Auth & proof
                    </span>
                    <div className="mt-3 space-y-2 text-sm text-white/72">
                      <p>DNS ownership token verified</p>
                      <p>Session handoff attached</p>
                      <p>ArmorIQ plan signing required</p>
                    </div>
                  </label>
                </div>
              </div>

              <div className="grid gap-4">
                {pipelineMetrics.map((metric) => (
                  <div
                    key={metric.label}
                    className="rounded-[24px] border border-white/10 bg-white/6 p-5"
                  >
                    <p className="text-sm text-white/60">{metric.label}</p>
                    <div className="mt-3 flex items-end justify-between">
                      <span className="text-4xl font-semibold text-white">
                        {metric.value}
                      </span>
                      <span className="text-sm text-[#9ec9a8]">
                        {metric.detail}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-6 grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
              <section className="rounded-[28px] border border-white/10 bg-white/6 p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-[0.3em] text-[#8db39d]">
                      Live queue
                    </p>
                    <h3 className="mt-2 text-2xl font-semibold text-white">
                      Scan operations
                    </h3>
                  </div>
                  <span className="rounded-full border border-white/10 px-3 py-2 text-xs uppercase tracking-[0.2em] text-white/55">
                    Celery + websockets
                  </span>
                </div>

                <div className="mt-5 space-y-4">
                  {scanQueue.map((scan) => (
                    <article
                      key={scan.name}
                      className="rounded-[24px] border border-white/10 bg-[#07111c] p-4"
                    >
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                        <div>
                          <p className="text-lg font-medium text-white">
                            {scan.name}
                          </p>
                          <p className="mt-1 text-sm text-white/60">
                            {scan.mode}
                          </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-3 text-sm">
                          <span className={getStatusStyle(scan.status)}>
                            {scan.status}
                          </span>
                          <span className="text-white/45">ETA {scan.eta}</span>
                          <span
                            className={`rounded-full px-3 py-1 ${getSeverityStyle(scan.risk)}`}
                          >
                            {scan.risk} risk
                          </span>
                        </div>
                      </div>

                      <div className="mt-4">
                        <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-[0.2em] text-white/45">
                          <span>Progress</span>
                          <span>{scan.progress}%</span>
                        </div>
                        <div className="h-2 rounded-full bg-white/8">
                          <div
                            className="h-2 rounded-full bg-[linear-gradient(90deg,_#d7f266,_#6dd7ae)]"
                            style={{ width: `${scan.progress}%` }}
                          />
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </section>

              <section className="rounded-[28px] border border-white/10 bg-white/6 p-5">
                <p className="text-xs uppercase tracking-[0.3em] text-[#8db39d]">
                  Audit stream
                </p>
                <h3 className="mt-2 text-2xl font-semibold text-white">
                  Policy activity
                </h3>
                <div className="mt-5 space-y-3">
                  {auditEvents.map((event, index) => (
                    <div
                      key={event}
                      className="rounded-[22px] border border-white/10 bg-[#07111c] p-4"
                    >
                      <p className="text-xs uppercase tracking-[0.25em] text-white/40">
                        Event {index + 1}
                      </p>
                      <p className="mt-2 text-sm leading-6 text-white/76">
                        {event}
                      </p>
                    </div>
                  ))}
                </div>
              </section>
            </div>

            <div className="mt-6 grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
              <section className="rounded-[28px] border border-white/10 bg-white/6 p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-[0.3em] text-[#8db39d]">
                      Findings
                    </p>
                    <h3 className="mt-2 text-2xl font-semibold text-white">
                      Validated vulnerabilities
                    </h3>
                  </div>
                  <button className="rounded-full border border-white/10 px-4 py-2 text-sm text-white/72 transition hover:bg-white/8">
                    Review all
                  </button>
                </div>

                <div className="mt-5 space-y-4">
                  {findings.map((finding) => (
                    <article
                      key={finding.title}
                      className="rounded-[24px] border border-white/10 bg-[#07111c] p-4"
                    >
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div>
                          <span
                            className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${getSeverityStyle(
                              finding.severity,
                            )}`}
                          >
                            {finding.severity}
                          </span>
                          <h4 className="mt-3 text-lg font-medium text-white">
                            {finding.title}
                          </h4>
                          <p className="mt-2 text-sm text-white/56">
                            {finding.location}
                          </p>
                        </div>
                        <div className="rounded-2xl border border-white/10 px-4 py-3 text-sm text-white/74">
                          Confidence {finding.confidence}
                        </div>
                      </div>
                      <p className="mt-4 text-sm leading-6 text-white/74">
                        {finding.summary}
                      </p>
                    </article>
                  ))}
                </div>
              </section>

              <section className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,_rgba(255,255,255,0.07),_rgba(255,255,255,0.04))] p-5">
                <p className="text-xs uppercase tracking-[0.3em] text-[#8db39d]">
                  Reports
                </p>
                <h3 className="mt-2 text-2xl font-semibold text-white">
                  Export surfaces
                </h3>

                <div className="mt-5 grid gap-4">
                  <div className="rounded-[24px] border border-white/10 bg-[#07111c] p-4">
                    <p className="text-sm font-medium text-white">
                      Executive summary PDF
                    </p>
                    <p className="mt-2 text-sm leading-6 text-white/64">
                      One-click report for compliance reviews, stakeholder
                      briefings, and remediation planning.
                    </p>
                  </div>

                  <div className="rounded-[24px] border border-white/10 bg-[#07111c] p-4">
                    <p className="text-sm font-medium text-white">
                      JSON evidence bundle
                    </p>
                    <p className="mt-2 text-sm leading-6 text-white/64">
                      Structured finding objects, reproduction details, and
                      immutable audit metadata.
                    </p>
                  </div>

                  <div className="rounded-[24px] border border-white/10 bg-[#07111c] p-4">
                    <p className="text-sm font-medium text-white">
                      SARIF developer handoff
                    </p>
                    <p className="mt-2 text-sm leading-6 text-white/64">
                      Pipeline-friendly export for GitHub Security and CI policy
                      gates.
                    </p>
                  </div>
                </div>

                <div className="mt-5 rounded-[24px] border border-[#d7f266]/20 bg-[#d7f266]/10 p-4">
                  <p className="text-xs uppercase tracking-[0.25em] text-[#d7f266]">
                    MVP note
                  </p>
                  <p className="mt-2 text-sm leading-6 text-white/74">
                    This Phase 2 UI gives the product a real control-plane shell
                    for the backend, agent, policy, and reporting phases to plug
                    into next.
                  </p>
                </div>
              </section>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
