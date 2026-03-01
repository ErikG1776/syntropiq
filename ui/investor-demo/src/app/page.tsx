"use client";

import Link from "next/link";
import {
  ShieldCheck,
  Landmark,
  HeartPulse,
  ArrowRight,
  Activity,
  Lock,
  Zap,
} from "lucide-react";

const domains = [
  {
    icon: ShieldCheck,
    title: "Payment Fraud",
    description: "Real-time transaction monitoring across 3 AI fraud detection models",
    color: "text-rose-400",
    border: "border-rose-500/20 hover:border-rose-500/40",
    glow: "hover:shadow-[0_0_30px_rgba(244,63,94,0.1)]",
    bg: "bg-rose-500/5",
  },
  {
    icon: Landmark,
    title: "Loan Underwriting",
    description: "Automated loan approval decisions across 3 underwriting AI agents",
    color: "text-cyan-400",
    border: "border-cyan-500/20 hover:border-cyan-500/40",
    glow: "hover:shadow-[0_0_30px_rgba(34,211,238,0.1)]",
    bg: "bg-cyan-500/5",
  },
  {
    icon: HeartPulse,
    title: "Hospital Readmission",
    description: "Discharge planning for diabetic patients across 3 clinical AI models",
    color: "text-emerald-400",
    border: "border-emerald-500/20 hover:border-emerald-500/40",
    glow: "hover:shadow-[0_0_30px_rgba(52,211,153,0.1)]",
    bg: "bg-emerald-500/5",
  },
];

const features = [
  {
    icon: Activity,
    title: "Drift Detection",
    description: "Monitors agent trust trajectories and detects performance degradation in real-time",
  },
  {
    icon: Lock,
    title: "Autonomous Suppression",
    description: "Automatically isolates underperforming agents while maintaining system throughput",
  },
  {
    icon: Zap,
    title: "Recursive Recovery",
    description: "Self-healing governance that adapts thresholds and restores agents through probation",
  },
];

export default function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 dot-grid opacity-40" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-cyan-500/[0.03] rounded-full blur-[120px]" />
      <div className="absolute bottom-0 right-0 w-[600px] h-[400px] bg-rose-500/[0.02] rounded-full blur-[100px]" />

      <div className="relative z-10">
        {/* Header */}
        <header className="flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center">
              <Activity className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-semibold tracking-tight">syntropiq</span>
          </div>
          <span className="text-xs font-mono text-text-muted bg-white/5 px-3 py-1.5 rounded-full border border-border">
            INVESTOR DEMO
          </span>
        </header>

        {/* Hero */}
        <main className="max-w-7xl mx-auto px-8 pt-20 pb-16">
          <div className="text-center max-w-3xl mx-auto mb-20">
            <div className="inline-flex items-center gap-2 text-xs font-mono text-cyan-400 bg-cyan-400/10 px-4 py-2 rounded-full border border-cyan-400/20 mb-8">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              Autonomous AI Governance Platform
            </div>

            <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-6 leading-[1.1]">
              AI agents that{" "}
              <span className="bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
                govern themselves
              </span>
            </h1>

            <p className="text-lg text-text-secondary max-w-2xl mx-auto mb-10 leading-relaxed">
              Watch multi-agent systems detect drift, suppress failing models,
              adapt governance thresholds, and recover — all without human
              intervention.
            </p>

            <Link
              href="/demo"
              className="inline-flex items-center gap-3 bg-gradient-to-r from-cyan-500 to-blue-500 text-white font-semibold px-8 py-4 rounded-xl text-base hover:from-cyan-400 hover:to-blue-400 transition-all duration-300 shadow-[0_0_30px_rgba(34,211,238,0.2)] hover:shadow-[0_0_50px_rgba(34,211,238,0.3)]"
            >
              Launch Live Demo
              <ArrowRight className="w-5 h-5" />
            </Link>
          </div>

          {/* Domain cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-20">
            {domains.map((d) => (
              <div
                key={d.title}
                className={`glass-card p-6 transition-all duration-300 ${d.border} ${d.glow}`}
              >
                <div className={`w-10 h-10 rounded-xl ${d.bg} flex items-center justify-center mb-4`}>
                  <d.icon className={`w-5 h-5 ${d.color}`} />
                </div>
                <h3 className="text-base font-semibold mb-2">{d.title}</h3>
                <p className="text-sm text-text-secondary leading-relaxed">
                  {d.description}
                </p>
              </div>
            ))}
          </div>

          {/* Feature strip */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            {features.map((f) => (
              <div key={f.title} className="text-center">
                <div className="w-10 h-10 rounded-xl bg-white/5 border border-border flex items-center justify-center mx-auto mb-3">
                  <f.icon className="w-5 h-5 text-text-secondary" />
                </div>
                <h4 className="text-sm font-semibold mb-1">{f.title}</h4>
                <p className="text-xs text-text-muted leading-relaxed">
                  {f.description}
                </p>
              </div>
            ))}
          </div>
        </main>

        {/* Footer */}
        <footer className="text-center py-8 text-xs text-text-muted border-t border-border">
          Patent-pending autonomous governance technology
        </footer>
      </div>
    </div>
  );
}
