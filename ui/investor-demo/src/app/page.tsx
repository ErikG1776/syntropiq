"use client";

import Link from "next/link";
import {
  ShieldCheck,
  Landmark,
  HeartPulse,
  ArrowRight,
  Activity,
  Shield,
  Zap,
  Eye,
} from "lucide-react";

const domains = [
  {
    icon: ShieldCheck,
    title: "Payment Fraud",
    subtitle: "Transaction Monitoring",
    description:
      "3 AI models score transactions in real time. When one drifts, governance suppresses it before losses compound.",
    color: "text-red-400",
    iconBg: "bg-red-500/10",
  },
  {
    icon: Landmark,
    title: "Loan Underwriting",
    subtitle: "Credit Decisioning",
    description:
      "3 underwriting agents compete on approval quality. Drift detection catches loosening standards before defaults spike.",
    color: "text-blue-400",
    iconBg: "bg-blue-500/10",
  },
  {
    icon: HeartPulse,
    title: "Hospital Readmission",
    subtitle: "Discharge Planning",
    description:
      "3 clinical models flag readmission risk. Governance catches model degradation before CMS penalties hit.",
    color: "text-emerald-400",
    iconBg: "bg-emerald-500/10",
  },
];

const capabilities = [
  {
    icon: Eye,
    title: "Drift Detection",
    description:
      "Continuous trust scoring detects performance degradation within 2\u20133 governance cycles",
  },
  {
    icon: Shield,
    title: "Autonomous Suppression",
    description:
      "Underperforming agents are isolated automatically \u2014 no human intervention, no production downtime",
  },
  {
    icon: Zap,
    title: "Recursive Recovery",
    description:
      "Self-healing governance adapts thresholds, rehabilitates agents through probation, and restores full capacity",
  },
];

export default function LandingPage() {
  return (
    <div className="relative min-h-screen">
      {/* Subtle background glow */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-[-20%] left-1/2 -translate-x-1/2 w-[900px] h-[600px] bg-blue-500/[0.04] rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[400px] bg-violet-500/[0.03] rounded-full blur-[100px]" />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto px-6">
        {/* Nav */}
        <header className="flex items-center justify-between py-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
              <Activity className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-semibold tracking-tight">
              syntropiq
            </span>
          </div>
          <div className="text-[11px] font-mono text-text-muted bg-surface px-4 py-2 rounded-full border border-border tracking-wider">
            INVESTOR DEMO
          </div>
        </header>

        {/* Hero */}
        <section className="pt-24 pb-20 text-center">
          <div className="inline-flex items-center gap-2 text-xs font-medium text-blue-400 bg-blue-500/10 px-4 py-2 rounded-full border border-blue-500/15 mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
            Autonomous AI Governance
          </div>

          <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold tracking-tight leading-[1.05] mb-6 max-w-4xl mx-auto">
            AI agents that{" "}
            <span className="bg-gradient-to-r from-blue-400 via-blue-300 to-violet-400 bg-clip-text text-transparent">
              govern themselves
            </span>
          </h1>

          <p className="text-lg md:text-xl text-text-secondary max-w-2xl mx-auto leading-relaxed mb-12">
            Watch multi-agent systems detect drift, suppress failing models,
            adapt thresholds, and self-heal &mdash; all without human intervention.
          </p>

          <Link
            href="/demo"
            className="group inline-flex items-center gap-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold px-8 py-4 rounded-xl text-base transition-all duration-200 shadow-[0_0_40px_rgba(59,130,246,0.25)] hover:shadow-[0_0_60px_rgba(59,130,246,0.35)]"
          >
            Launch Live Demo
            <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </section>

        {/* Domain Cards */}
        <section className="pb-20">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {domains.map((d) => (
              <div
                key={d.title}
                className="panel p-6 hover:border-border-bright transition-all duration-300"
              >
                <div
                  className={`w-10 h-10 rounded-xl ${d.iconBg} flex items-center justify-center mb-5`}
                >
                  <d.icon className={`w-5 h-5 ${d.color}`} />
                </div>
                <p className="text-[11px] font-medium text-text-muted uppercase tracking-wider mb-1.5">
                  {d.subtitle}
                </p>
                <h3 className="text-lg font-semibold mb-2">{d.title}</h3>
                <p className="text-sm text-text-secondary leading-relaxed">
                  {d.description}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Capabilities */}
        <section className="pb-24">
          <div className="text-center mb-12">
            <h2 className="text-2xl font-bold tracking-tight mb-3">
              How it works
            </h2>
            <p className="text-sm text-text-secondary max-w-lg mx-auto">
              Three layers of autonomous governance, running continuously
              without human oversight.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            {capabilities.map((c, i) => (
              <div key={c.title} className="text-center">
                <div className="w-12 h-12 rounded-2xl bg-surface border border-border flex items-center justify-center mx-auto mb-4">
                  <c.icon className="w-5 h-5 text-text-secondary" />
                </div>
                <div className="text-[11px] font-mono text-text-muted mb-2">
                  0{i + 1}
                </div>
                <h4 className="text-sm font-semibold mb-2">{c.title}</h4>
                <p className="text-xs text-text-muted leading-relaxed">
                  {c.description}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Footer */}
        <footer className="py-8 border-t border-border flex items-center justify-between text-xs text-text-muted">
          <span>Patent-pending autonomous governance technology</span>
          <span className="font-mono">syntropiq.com</span>
        </footer>
      </div>
    </div>
  );
}
