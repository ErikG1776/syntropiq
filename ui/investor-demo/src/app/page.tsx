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
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

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
        <div className="absolute top-[10%] left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-primary/[0.04] rounded-full blur-[150px]" />
      </div>

      {/* ── Nav ─────────────────────────────────────────────────── */}
      <nav className="relative z-10 border-b border-border">
        <div className="max-w-5xl mx-auto px-6 flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <Activity className="w-4 h-4 text-white" />
            </div>
            <span className="text-base font-semibold tracking-tight">
              syntropiq
            </span>
          </div>
          <span className="text-[11px] font-mono text-muted-foreground tracking-wider">
            INVESTOR DEMO
          </span>
        </div>
      </nav>

      {/* ── Hero (fills viewport) ───────────────────────────────── */}
      <section className="relative z-10 flex flex-col items-center justify-center text-center px-6 min-h-[calc(100vh-4rem)]">
        <div className="max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 text-xs font-medium text-primary bg-primary/10 px-4 py-2 rounded-full border border-primary/20 mb-10">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            Autonomous AI Governance
          </div>

          <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight leading-[1.1] mb-8">
            AI agents that{" "}
            <span className="bg-gradient-to-r from-blue-400 to-violet-400 bg-clip-text text-transparent">
              govern themselves.
            </span>
          </h1>

          <p className="text-base sm:text-lg text-muted-foreground max-w-xl mx-auto leading-relaxed mb-12">
            Watch multi-agent systems detect drift, suppress failing models,
            adapt thresholds, and self-heal &mdash; all without human
            intervention.
          </p>

          <div className="flex items-center justify-center gap-4">
            <Link href="/demo">
              <Button
                size="lg"
                className="shadow-[0_0_30px_rgba(59,130,246,0.2)] hover:shadow-[0_0_50px_rgba(59,130,246,0.3)] transition-shadow"
              >
                Launch Live Demo
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* ── Domain Cards ────────────────────────────────────────── */}
      <section className="relative z-10 border-t border-border">
        <div className="max-w-5xl mx-auto px-6 py-24">
          <div className="mb-16 max-w-xl">
            <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-3">
              Live Scenarios
            </p>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
              Three domains. Real governance.
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {domains.map((d) => (
              <Card
                key={d.title}
                className="hover:border-muted-foreground/20 transition-colors"
              >
                <CardContent className="p-6">
                  <div
                    className={`w-10 h-10 rounded-xl ${d.iconBg} flex items-center justify-center mb-5`}
                  >
                    <d.icon className={`w-5 h-5 ${d.color}`} />
                  </div>
                  <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-1.5">
                    {d.subtitle}
                  </p>
                  <h3 className="text-base font-semibold mb-3">{d.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {d.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Works ────────────────────────────────────────── */}
      <section className="relative z-10 border-t border-border">
        <div className="max-w-5xl mx-auto px-6 py-24">
          <div className="text-center mb-16">
            <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-3">
              Under the Hood
            </p>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
              How it works
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 max-w-4xl mx-auto">
            {capabilities.map((c, i) => (
              <div key={c.title} className="text-center">
                <div className="w-12 h-12 rounded-xl bg-card border border-border flex items-center justify-center mx-auto mb-5">
                  <c.icon className="w-5 h-5 text-muted-foreground" />
                </div>
                <div className="text-[11px] font-mono text-muted-foreground mb-3">
                  0{i + 1}
                </div>
                <h4 className="text-sm font-semibold mb-2">{c.title}</h4>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {c.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────── */}
      <footer className="relative z-10 border-t border-border">
        <div className="max-w-5xl mx-auto px-6 py-8 flex items-center justify-between text-xs text-muted-foreground">
          <span>Patent-pending autonomous governance technology</span>
          <span className="font-mono">syntropiq.com</span>
        </div>
      </footer>
    </div>
  );
}
