import React, { useRef, useState } from "react";
import brainIcon from "./assets/brain.png";

type RiskContributor = { feature: string; impact: number };
type BrainResponse = {
  risk_score: number;
  risk_band: "Low" | "Medium" | "High";
  top_contributors: RiskContributor[];
};

type VisionDetection = {
  cls: string;
  bbox: [number, number, number, number];
  conf: number;
};

type VisionResponse = {
  detections: VisionDetection[];
  persons: number;
  helmeted_persons: number;
  compliance_rate: number;
  overlay_url?: string;
};

type ScribeIssue = { type: string; summary: string };
type ScribeResponse = {
  date?: string;
  project?: string;
  location?: string;
  subcontractors?: string[];
  personnel_count?: number | null;
  completed_tasks?: string[];
  issues?: ScribeIssue[];
  safety_observations?: string[];
  low_confidence?: boolean;
  confidence?: Record<string, number>;
  export_csv_url?: string;
};

const BRAND = {
  background:
    "radial-gradient(140% 180% at 0% 0%, rgba(16, 185, 129, 0.14), rgba(0, 0, 0, 0)) , radial-gradient(120% 200% at 100% 0%, rgba(52, 211, 153, 0.12), rgba(0, 0, 0, 0)) , linear-gradient(180deg, #000000 0%, #020617 45%, #000000 95%)",
  surface: "linear-gradient(145deg, rgba(17, 24, 39, 0.94), rgba(0, 0, 0, 0.92))",
  surfaceAlt: "linear-gradient(145deg, rgba(24, 32, 45, 0.9), rgba(2, 8, 23, 0.94))",
  primary: "#22c55e",
  text: "#F9FAFB",
  muted: "#9CA3AF",
  border: "rgba(31, 41, 55, 0.85)",
} as const;

const API_BASE =
  import.meta.env.VITE_API_BASE?.toString() || "http://localhost:8000";

const SectionHeader: React.FC<{ title: string; subtitle: string }> = ({
  title,
  subtitle,
}) => (
  <div className="mb-12 max-w-3xl">
    <h2 className="font-display text-3xl tracking-tight text-roshn-ink md:text-4xl bg-gradient-to-r from-emerald-400 to-emerald-600 bg-clip-text text-transparent">
      {title}
    </h2>
    <p className="mt-4 text-base text-roshn-muted md:text-lg leading-relaxed">{subtitle}</p>
    <div className="mt-6 h-1 w-20 rounded-full bg-gradient-to-r from-emerald-500 to-emerald-400" />
  </div>
);

const Card: React.FC<React.PropsWithChildren<{ className?: string }>> = ({
  className = "",
  children,
}) => (
  <div
    className={`rounded-3xl border border-gray-800 p-6 shadow-soft backdrop-blur md:p-8 ${className}`}
    style={{ background: BRAND.surface }}
  >
    {children}
  </div>
);

const Pill: React.FC<{
  tone?: "ok" | "warn" | "bad";
  children: React.ReactNode;
}> = ({ tone, children }) => {
  const palette = {
    ok: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    warn: "border-yellow-500/30 bg-yellow-500/10 text-yellow-300",
    bad: "border-red-500/40 bg-red-500/10 text-red-300",
  } as const;
  const base =
    "inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold tracking-wide";
  const toneClass = tone
    ? palette[tone]
    : "border-emerald-500/20 bg-emerald-500/5 text-emerald-300";
  return <span className={`${base} ${toneClass}`}>{children}</span>;
};

const ResultBox: React.FC<{ data: unknown; empty: string }> = ({
  data,
  empty,
}) =>
  data ? (
    <pre
      className="max-h-64 overflow-auto rounded-2xl border border-gray-800 bg-gray-900/70 p-4 font-mono text-xs leading-relaxed text-roshn-ink"
      style={{ background: BRAND.surfaceAlt }}
    >
      {pretty(data)}
    </pre>
  ) : (
    <div
      className="rounded-2xl border border-dashed border-gray-800 bg-gray-900/60 p-4 text-sm text-roshn-muted"
      style={{ background: BRAND.surfaceAlt }}
    >
      {empty}
    </div>
  );

function pretty(value: unknown) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export default function App() {
  const [busy, setBusy] = useState<null | "brain" | "vision" | "scribe">(null);

  // Add smooth scroll behavior to html element
  React.useEffect(() => {
    document.documentElement.style.scrollBehavior = 'smooth';
    return () => {
      document.documentElement.style.scrollBehavior = 'auto';
    };
  }, []);

  const [brainJson, setBrainJson] = useState(() =>
    JSON.stringify(
      {
        features: {
          Budget: 120_000_000,
          Duration_days: 540,
          Complexity: "High",
          Region: "Riyadh",
          Contractor_Tier: "Tier1",
          Buffer_days: 15,
        },
      },
      null,
      2
    )
  );
  const [brainResult, setBrainResult] = useState<BrainResponse | null>(null);

  const [visionResult, setVisionResult] = useState<VisionResponse | null>(null);
  const [visionOverlay, setVisionOverlay] = useState<string | null>(null);
  const [visionFileName, setVisionFileName] = useState<string>("");
  const visionFileRef = useRef<HTMLInputElement | null>(null);

  const [scribeText, setScribeText] = useState("");
  const [scribeResult, setScribeResult] = useState<ScribeResponse | null>(null);
  const scribeFileRef = useRef<HTMLInputElement | null>(null);

  const brainTone: "ok" | "warn" | "bad" | undefined = brainResult
    ? brainResult.risk_band === "Low"
      ? "ok"
      : brainResult.risk_band === "Medium"
      ? "warn"
      : "bad"
    : undefined;

  const compliancePct =
    typeof visionResult?.compliance_rate === "number"
      ? Math.round((visionResult.compliance_rate ?? 0) * 100)
      : null;

  const complianceTone: "ok" | "warn" | "bad" | undefined =
    compliancePct === null
      ? undefined
      : compliancePct >= 90
      ? "ok"
      : compliancePct >= 70
      ? "warn"
      : "bad";

  const compliancePanelClass =
    complianceTone === "ok"
      ? "border-emerald-500/30 bg-emerald-500/10"
      : complianceTone === "warn"
      ? "border-yellow-500/30 bg-yellow-500/10"
      : complianceTone === "bad"
      ? "border-red-500/40 bg-red-500/10"
      : "border-gray-800 bg-gray-900/60";

  async function submitBrain(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    let payload: unknown;
    try {
      payload = JSON.parse(brainJson || "{}");
    } catch {
      alert("JSON is invalid. Please fix the payload and try again.");
      return;
    }

    setBusy("brain");
    try {
      const response = await fetch(`${API_BASE}/predict-delay`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const data = (await response.json()) as BrainResponse;
      setBrainResult(data);
    } catch (error) {
      console.error(error);
      alert("Unable to score the project right now. Check the backend.");
    } finally {
      setBusy(null);
    }
  }

  async function submitVision(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = visionFileRef.current?.files?.[0];
    if (!file) {
      alert("Please choose an image file first.");
      return;
    }

    setBusy("vision");
    try {
      const form = new FormData();
      form.append("file", file);
      const response = await fetch(`${API_BASE}/analyze-image`, {
        method: "POST",
        body: form,
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const data = (await response.json()) as VisionResponse;
      setVisionResult(data);
      setVisionOverlay(
        data?.overlay_url ? `${API_BASE}${data.overlay_url}` : null
      );
      setVisionFileName(file.name);
    } catch (error) {
      console.error(error);
      alert("Unable to analyse the image. Please check the backend logs.");
    } finally {
      setBusy(null);
    }
  }

  async function submitScribeFile(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = scribeFileRef.current?.files?.[0];
    if (!file) {
      alert("Please select a PDF or text file.");
      return;
    }

    setBusy("scribe");
    try {
      const form = new FormData();
      form.append("file", file);
      const response = await fetch(`${API_BASE}/extract`, {
        method: "POST",
        body: form,
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const data = (await response.json()) as ScribeResponse;
      setScribeResult(data);
    } catch (error) {
      console.error(error);
      alert("File extraction failed. Check the backend service.");
    } finally {
      setBusy(null);
    }
  }

  async function submitScribeText(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!scribeText.trim()) {
      return;
    }

    setBusy("scribe");
    try {
      const response = await fetch(`${API_BASE}/extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: scribeText }),
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const data = (await response.json()) as ScribeResponse;
      setScribeResult(data);
    } catch (error) {
      console.error(error);
      alert("Text extraction failed. Please retry once the backend is ready.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div
      className="min-h-screen w-full font-sans text-roshn-ink scroll-smooth"
      style={{ background: BRAND.background }}
    >
      <style>{`
        html {
          scroll-behavior: smooth;
        }
        
        @keyframes flowingMesh {
          0% {
            background-position: 0% 0%;
            opacity: 0.6;
          }
          33% {
            background-position: 100% 50%;
            opacity: 0.8;
          }
          66% {
            background-position: 50% 100%;
            opacity: 0.7;
          }
          100% {
            background-position: 0% 0%;
            opacity: 0.6;
          }
        }
        
        .flowing-header {
          overflow: hidden;
        }
        
        .flowing-header::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: radial-gradient(
            ellipse at 20% 50%,
            rgba(16, 185, 129, 0.15) 0%,
            transparent 50%
          ),
          radial-gradient(
            ellipse at 80% 20%,
            rgba(52, 211, 153, 0.12) 0%,
            transparent 50%
          ),
          radial-gradient(
            ellipse at 60% 80%,
            rgba(16, 185, 129, 0.1) 0%,
            transparent 50%
          );
          background-size: 300% 300%;
          animation: flowingMesh 20s ease-in-out infinite;
          pointer-events: none;
        }
      `}</style>
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-gray-800 bg-black/95 backdrop-blur-md flowing-header">
        <div className="mx-auto flex w-full max-w-screen-2xl items-center justify-between px-6 py-4 lg:px-12 relative z-10">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-20 items-center justify-center rounded-2xl border border-gray-800 bg-[radial-gradient(circle_at_top,rgba(34,197,94,0.2)_0%,rgba(0,0,0,0.85)_100%)] shadow-[0_12px_32px_rgba(16,185,129,0.25)]">
              <img src="/roshn-logo.png" alt="ROSHN Pulse Logo" className="h-14 w-18" />
            </div>
            <div>
              <div className="font-display text-lg font-semibold tracking-wide text-roshn-accent">
                ROSHN PULSE
              </div>
              <div className="text-xs uppercase tracking-wide text-roshn-muted">
                Safety / Risk / Reporting
              </div>
            </div>
          </div>
          <nav className="hidden gap-3 text-sm font-bold text-roshn-muted md:flex">
            <a href="#brain" className="relative px-4 py-2 rounded-lg transition-all duration-300 hover:text-emerald-300 hover:bg-emerald-500/10 group border border-transparent hover:border-emerald-500/30 uppercase tracking-wider">
              <span className="relative z-10">Brain</span>
              <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-0 h-0.5 bg-gradient-to-r from-emerald-500 to-emerald-400 group-hover:w-3/4 transition-all duration-300 rounded-full" />
            </a>
            <a href="#vision" className="relative px-4 py-2 rounded-lg transition-all duration-300 hover:text-emerald-300 hover:bg-emerald-500/10 group border border-transparent hover:border-emerald-500/30 uppercase tracking-wider">
              <span className="relative z-10">Vision</span>
              <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-0 h-0.5 bg-gradient-to-r from-emerald-500 to-emerald-400 group-hover:w-3/4 transition-all duration-300 rounded-full" />
            </a>
            <a href="#scribe" className="relative px-4 py-2 rounded-lg transition-all duration-300 hover:text-emerald-300 hover:bg-emerald-500/10 group border border-transparent hover:border-emerald-500/30 uppercase tracking-wider">
              <span className="relative z-10">Scribe</span>
              <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-0 h-0.5 bg-gradient-to-r from-emerald-500 to-emerald-400 group-hover:w-3/4 transition-all duration-300 rounded-full" />
            </a>
          </nav>
          <a
            href="#brain"
            className="rounded-full bg-gradient-to-r from-emerald-500 via-emerald-500 to-green-400 px-5 py-2 text-sm font-semibold text-gray-900 shadow-[0_20px_40px_rgba(16,185,129,0.35)] transition hover:from-emerald-400 hover:to-green-300"
          >
            Get Started
          </a>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="relative min-h-screen overflow-hidden">
          <div className="absolute inset-0 -z-10 bg-gradient-to-br from-black via-gray-900 to-black" />
          <div className="absolute -left-28 top-16 -z-10 h-72 w-72 rounded-full bg-[radial-gradient(circle_at_center,rgba(34,197,94,0.28)0%,rgba(0,0,0,0)70%)] blur-3xl" />
          <div className="absolute -right-24 bottom-10 -z-10 h-80 w-80 rounded-full bg-[radial-gradient(circle_at_center,rgba(52,211,153,0.26)0%,rgba(0,0,0,0)75%)] blur-3xl" />

          <div className="mx-auto flex w-full max-w-screen-2xl flex-col gap-16 px-6 py-16 text-roshn-ink lg:px-12">
            <div className="flex flex-col lg:flex-row gap-8 items-start justify-between">
              <div className="max-w-2xl">
                <p className="font-display text-sm uppercase tracking-[0.5em] text-roshn-muted">
                  Roshn Intelligence Suite
                </p>
                <h1 className="mt-6 font-display text-4xl leading-tight text-roshn-ink md:text-6xl">
                  Build safer, smarter, giga-scale projects.
                </h1>
                <p className="mt-6 text-base text-roshn-muted md:text-lg">
                  A unified front-end for delay prediction, PPE compliance, and
                  automatic report extraction. Crafted to mirror the energy and
                  elegance of the ROSHN Hackathon experience.
                </p>
                <div className="mt-8 flex flex-wrap gap-4">
                  <a
                    href="#brain"
                    className="rounded-full bg-gradient-to-r from-emerald-500 via-emerald-500 to-green-400 px-6 py-3 text-sm font-semibold text-gray-900 shadow-[0_22px_48px_rgba(16,185,129,0.32)] transition hover:from-emerald-400 hover:to-green-300"
                  >
                    Explore Risk
                  </a>
                  <a
                    href="#vision"
                    className="rounded-full border border-gray-800 px-6 py-3 text-sm font-semibold text-emerald-300 transition hover:border-emerald-500/40 hover:bg-emerald-500/10"
                  >
                    Analyse Safety
                  </a>
                </div>
              </div>

              <Card className="border-emerald-500/20 text-roshn-ink shadow-[0_32px_70px_rgba(16,185,129,0.22)] lg:min-w-[420px] lg:mt-14">
                <div className="grid gap-5 md:grid-cols-2">
                  <div>
                    <div className="text-xs font-semibold tracking-wide text-roshn-muted">
                      Latest Risk Score
                    </div>
                    <div className="mt-3 text-3xl font-semibold text-roshn-ink">
                      {(brainResult?.risk_score ?? 0.73).toFixed(2)}
                    </div>
                    <div className="mt-3">
                      <Pill tone={brainTone}>
                        {brainResult?.risk_band ?? "High"}
                      </Pill>
                    </div>
                  </div>

                  <div>
                    <div className="text-xs font-semibold tracking-wide text-roshn-muted">
                      PPE Compliance
                    </div>
                    <div className="mt-3 text-3xl font-semibold text-roshn-ink">
                      {typeof compliancePct === "number"
                        ? `${compliancePct}%`
                        : "84%"}
                    </div>
                    <div className="mt-3">
                      <Pill tone={complianceTone}>
                        {compliancePct === null
                          ? "Awaiting data"
                          : complianceTone === "ok"
                          ? "On Track"
                          : complianceTone === "warn"
                          ? "Monitor"
                          : "Critical"}
                      </Pill>
                    </div>
                  </div>

                  <div className="md:col-span-2 rounded-2xl border border-gray-800 bg-gray-900/60 p-4 text-sm text-roshn-muted">
                    {brainResult
                      ? "Insights refreshed from live predictions."
                      : "Schedule buffers and material logistics are driving risk this week. Two PPE exceptions in Zone C were resolved within four hours."}
                  </div>
                </div>
              </Card>
            </div>

            <div className="mx-auto grid max-w-5xl gap-4 sm:grid-cols-3">
              <div className="group relative overflow-hidden rounded-2xl border border-gray-800 bg-gray-900/60 p-5 shadow-[0_18px_36px_rgba(16,185,129,0.12)] transition hover:border-emerald-500/30">
                <div className="absolute inset-0 -z-10 bg-gradient-to-br from-emerald-500/10 via-transparent to-transparent opacity-0 transition group-hover:opacity-100" />
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/15 ring-1 ring-emerald-500/30">
                  <img
                    src={brainIcon}
                    alt="Brain icon"
                    className="h-8 w-8 object-contain"
                    style={{
                      filter:
                        "brightness(0) saturate(100%) invert(69%) sepia(63%) saturate(642%) hue-rotate(92deg) brightness(80%) contrast(98%)",
                    }}
                  />
                </div>
                <div className="mt-5 text-xs font-semibold uppercase tracking-widest text-emerald-300">
                  Brain
                </div>
                <div className="mt-3 text-lg font-semibold text-roshn-ink">
                  AI Risk Forecasting
                </div>
                <p className="mt-2 text-sm text-roshn-muted">
                  Surface probability of delay and contributing factors before schedules slip.
                </p>
              </div>
              <div className="group relative overflow-hidden rounded-2xl border border-gray-800 bg-gray-900/60 p-5 shadow-[0_18px_36px_rgba(16,185,129,0.12)] transition hover:border-emerald-500/30">
                <div className="absolute inset-0 -z-10 bg-gradient-to-br from-cyan-400/10 via-transparent to-transparent opacity-0 transition group-hover:opacity-100" />
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-cyan-400/15 text-cyan-300 ring-1 ring-cyan-400/30">
                  <svg
                    aria-hidden="true"
                    viewBox="0 0 24 24"
                    className="h-6 w-6"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12Z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                </div>
                <div className="mt-5 text-xs font-semibold uppercase tracking-widest text-emerald-300">
                  Vision
                </div>
                <div className="mt-3 text-lg font-semibold text-roshn-ink">
                  Live PPE Compliance
                </div>
                <p className="mt-2 text-sm text-roshn-muted">
                  Detect crews, helmets, and compliance rates from site imagery in seconds.
                </p>
              </div>
              <div className="group relative overflow-hidden rounded-2xl border border-gray-800 bg-gray-900/60 p-5 shadow-[0_18px_36px_rgba(16,185,129,0.12)] transition hover:border-emerald-500/30">
                <div className="absolute inset-0 -z-10 bg-gradient-to-br from-lime-400/10 via-transparent to-transparent opacity-0 transition group-hover:opacity-100" />
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-lime-400/15 text-lime-300 ring-1 ring-lime-400/30">
                  <svg
                    aria-hidden="true"
                    viewBox="0 0 24 24"
                    className="h-6 w-6"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M8 4h8a2 2 0 0 1 2 2v14l-6-3-6 3V6a2 2 0 0 1 2-2Z" />
                    <path d="M9 9h6" />
                    <path d="M9 13h6" />
                  </svg>
                </div>
                <div className="mt-5 text-xs font-semibold uppercase tracking-widest text-emerald-300">
                  Scribe
                </div>
                <div className="mt-3 text-lg font-semibold text-roshn-ink">
                  Instant Field Reports
                </div>
                <p className="mt-2 text-sm text-roshn-muted">
                  Turn PDFs and raw notes into structured insights ready for stakeholder updates.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Brain */}
        <section
          id="brain"
          className="border-t border-gray-800 bg-gradient-to-b from-black via-gray-900/80 to-black scroll-mt-28 min-h-screen"
        >
          <div className="mx-auto w-full max-w-screen-2xl px-6 py-16 lg:px-12">
            <SectionHeader
              title="Risk of Delay - Brain"
              subtitle="Send a feature payload to receive a calibrated risk score with the strongest drivers."
            />

            <div className="grid gap-8 lg:grid-cols-2">
              <Card>
                <form onSubmit={submitBrain} className="space-y-4">
                  <div>
                    <label className="text-sm font-semibold text-roshn-ink">
                      Payload (JSON)
                    </label>
                    <textarea
                      className="mt-2 h-56 w-full resize-y rounded-2xl border border-gray-800 bg-gray-900/70 p-4 font-mono text-xs text-roshn-ink outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/30"
                      value={brainJson}
                      onChange={(event) => setBrainJson(event.target.value)}
                    />
                  </div>
                  <div className="flex items-center justify-between text-xs text-roshn-muted">
                    <div>
                      Endpoint:{" "}
                      <code className="font-mono font-semibold text-roshn-accent">
                        POST /predict-delay
                      </code>
                    </div>
                    <button
                      type="submit"
                      disabled={busy === "brain"}
                      className="rounded-full bg-gradient-to-r from-emerald-500 via-emerald-500 to-green-400 px-5 py-2 text-sm font-semibold text-gray-900 shadow-soft transition hover:from-emerald-400 hover:to-green-300 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {busy === "brain" ? "Scoring..." : "Score Project"}
                    </button>
                  </div>
                </form>
              </Card>

              <Card>
                <div className="flex items-center justify-between">
                  <div className="text-sm font-semibold text-roshn-ink">
                    Result
                  </div>
                  {brainResult?.risk_band && (
                    <Pill tone={brainTone}>{brainResult.risk_band}</Pill>
                  )}
                </div>
                <div className="mt-4">
                  <ResultBox data={brainResult} empty="Results will appear here after you score a project." />
                </div>
                {brainResult?.top_contributors?.length ? (
                  <div className="mt-5 space-y-2">
                    <div className="text-xs font-semibold uppercase tracking-wide text-roshn-muted">
                      Top Contributors
                    </div>
                    <ul className="grid gap-2 text-sm text-roshn-ink md:grid-cols-2">
                      {brainResult.top_contributors.slice(0, 6).map((item) => (
                        <li
                          key={item.feature}
                          className="rounded-xl border border-gray-800 bg-gray-900/60 px-3 py-2"
                        >
                          <div className="font-semibold">{item.feature}</div>
                          <div className="text-xs text-roshn-muted">
                            Impact {item.impact.toFixed(3)}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </Card>
            </div>
          </div>
        </section>

        {/* Vision */}
        <section
          id="vision"
          className="border-t border-gray-800 bg-gradient-to-b from-black via-gray-900/75 to-black scroll-mt-28 min-h-screen"
        >
          <div className="mx-auto w-full max-w-screen-2xl px-6 py-16 lg:px-12">
            <SectionHeader
              title="PPE Compliance - Vision"
              subtitle="Upload a site image to detect crew, helmets, and calculate compliance."
            />

            <div className="grid gap-8 lg:grid-cols-2">
              <Card>
                <form onSubmit={submitVision} className="space-y-4">
                  <div>
                    <label className="text-sm font-semibold text-roshn-ink">
                      Site image
                    </label>
                    <input
                      ref={visionFileRef}
                      type="file"
                      accept="image/*"
                      onChange={(event) => {
                        const file = event.target.files?.[0];
                        setVisionFileName(file ? file.name : "");
                      }}
                      className="mt-2 block w-full cursor-pointer rounded-2xl border border-dashed border-gray-800 bg-gray-900/60 p-4 text-sm text-roshn-ink transition hover:border-emerald-500/40 file:mr-4 file:rounded-full file:border-0 file:bg-emerald-500 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-gray-900"
                    />
                    {visionFileName && (
                      <div className="mt-2 text-xs text-roshn-muted">
                        Selected: {visionFileName}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center justify-between text-xs text-roshn-muted">
                    <div>
                      Endpoint:{" "}
                      <code className="font-mono font-semibold text-roshn-accent">
                        POST /analyze-image
                      </code>
                    </div>
                    <button
                      type="submit"
                      disabled={busy === "vision"}
                      className="rounded-full bg-gradient-to-r from-emerald-500 via-emerald-500 to-green-400 px-5 py-2 text-sm font-semibold text-gray-900 shadow-soft transition hover:from-emerald-400 hover:to-green-300 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {busy === "vision" ? "Analysing..." : "Analyse Image"}
                    </button>
                  </div>
                </form>
              </Card>

              <Card>
                <div className="grid gap-5 md:grid-cols-2">
                  <div>
                    <div className="text-sm font-semibold text-roshn-ink">
                      Detection JSON
                    </div>
                    <div className="mt-3">
                      <ResultBox
                        data={visionResult}
                        empty="Detections will appear here once the model responds."
                      />
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div>
                      <div className="text-sm font-semibold text-roshn-ink">
                        Overlay
                      </div>
                      <div
                        className="mt-3 overflow-hidden rounded-2xl border border-gray-800"
                        style={{ background: BRAND.surfaceAlt }}
                      >
                        {visionOverlay ? (
                          <img
                            src={visionOverlay}
                            alt="PPE overlay"
                            className="block w-full"
                          />
                        ) : (
                          <div className="flex h-56 items-center justify-center text-xs text-roshn-muted">
                            No overlay yet
                          </div>
                        )}
                      </div>
                    </div>
                    {visionResult ? (
                      <div className="grid grid-cols-3 gap-3 text-center text-sm">
                        <div className="rounded-2xl border border-blue-500/30 bg-blue-500/10 p-3">
                          <div className="text-xs uppercase text-roshn-muted">
                            Persons
                          </div>
                          <div className="mt-1 text-lg font-semibold text-roshn-ink">
                            {visionResult.persons}
                          </div>
                        </div>
                        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-3">
                          <div className="text-xs uppercase text-roshn-muted">
                            Helmeted
                          </div>
                          <div className="mt-1 text-lg font-semibold text-roshn-ink">
                            {visionResult.helmeted_persons}
                          </div>
                        </div>
                        <div className={`rounded-2xl p-3 ${compliancePanelClass}`}>
                          <div className="text-xs uppercase text-roshn-muted">
                            Compliance
                          </div>
                          <div className="mt-1 text-lg font-semibold text-roshn-ink">
                            {typeof compliancePct === "number"
                              ? `${compliancePct}%`
                              : "--"}
                          </div>
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </section>

        {/* Scribe */}
        <section
          id="scribe"
          className="border-t border-gray-800 bg-gradient-to-b from-black via-gray-900/75 to-black scroll-mt-28 min-h-screen"
        >
          <div className="mx-auto w-full max-w-screen-2xl px-6 py-16 lg:px-12">
            <SectionHeader
              title="Auto-extract Reports - Scribe"
              subtitle="Upload a report PDF or paste raw notes to generate structured fields instantly."
            />

            <div className="grid gap-8 lg:grid-cols-2">
              <Card>
                <form onSubmit={submitScribeFile} className="space-y-4">
                  <div>
                    <label className="text-sm font-semibold text-roshn-ink">
                      Upload PDF / Text file
                    </label>
                    <input
                      ref={scribeFileRef}
                      type="file"
                      accept=".pdf,.txt"
                      className="mt-2 block w-full cursor-pointer rounded-2xl border border-dashed border-gray-800 bg-gray-900/60 p-4 text-sm text-roshn-ink transition hover:border-emerald-500/40 file:mr-4 file:rounded-full file:border-0 file:bg-emerald-500 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-gray-900"
                    />
                  </div>
                  <div className="flex items-center justify-between text-xs text-roshn-muted">
                    <div>
                      Endpoint:{" "}
                      <code className="font-mono font-semibold text-roshn-accent">
                        POST /extract
                      </code>
                    </div>
                    <button
                      type="submit"
                      disabled={busy === "scribe"}
                      className="rounded-full bg-gradient-to-r from-emerald-500 via-emerald-500 to-green-400 px-5 py-2 text-sm font-semibold text-gray-900 shadow-soft transition hover:from-emerald-400 hover:to-green-300 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {busy === "scribe" ? "Extracting..." : "Extract from File"}
                    </button>
                  </div>
                </form>

                <div className="my-8 h-px bg-gray-800" />

                <form onSubmit={submitScribeText} className="space-y-4">
                  <label className="text-sm font-semibold text-roshn-ink">
                    ...or paste text
                  </label>
                  <textarea
                    className="mt-2 h-40 w-full resize-y rounded-2xl border border-gray-800 bg-gray-900/70 p-4 text-sm text-roshn-ink outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/30"
                    placeholder="Crew: 42 - Acme MEP - Two incidents in Zone A - Concrete pour completed..."
                    value={scribeText}
                    onChange={(event) => setScribeText(event.target.value)}
                  />
                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={busy === "scribe" || !scribeText.trim()}
                      className="rounded-full bg-gradient-to-r from-emerald-500 via-emerald-500 to-green-400 px-5 py-2 text-sm font-semibold text-gray-900 shadow-soft transition hover:from-emerald-400 hover:to-green-300 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {busy === "scribe" ? "Extracting..." : "Extract from Text"}
                    </button>
                  </div>
                </form>
              </Card>

              <Card>
                <div className="text-sm font-semibold text-roshn-ink">
                  Result
                </div>
                <div className="mt-4">
                  <ResultBox
                    data={scribeResult}
                    empty="Structured output will appear here after extraction."
                  />
                </div>

                {scribeResult?.issues?.length ? (
                  <div className="mt-5 space-y-2">
                    <div className="text-xs font-semibold uppercase tracking-wide text-roshn-muted">
                      Issues Highlighted
                    </div>
                    <ul className="grid gap-2 text-sm text-roshn-ink md:grid-cols-2">
                      {scribeResult.issues.slice(0, 6).map((issue, idx) => (
                        <li
                          key={`${issue.type}-${idx}`}
                          className="rounded-xl border border-gray-800 bg-gray-900/60 px-3 py-2"
                        >
                          <div className="font-semibold">{issue.type}</div>
                          <div className="text-xs text-roshn-muted">
                            {issue.summary}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {scribeResult?.export_csv_url ? (
                  <a
                    href={`${API_BASE}${scribeResult.export_csv_url}`}
                    className="mt-5 inline-flex items-center justify-center rounded-full bg-gradient-to-r from-emerald-500 via-emerald-500 to-green-400 px-5 py-2 text-sm font-semibold text-gray-900 shadow-soft transition hover:from-emerald-400 hover:to-green-300"
                  >
                    Download CSV
                  </a>
                ) : null}
              </Card>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 bg-gradient-to-t from-black via-gray-900/70 to-black">
        <div className="mx-auto flex w-full max-w-screen-2xl flex-col items-center justify-between gap-4 px-6 py-8 text-sm text-roshn-muted lg:flex-row lg:px-12">
          <div>
            Copyright © {new Date().getFullYear()} ROSHN PULSE
          </div>
          <div className="flex items-center gap-2">
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: BRAND.primary }}
            />
            <span>Quality / Safety / Delivery</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
