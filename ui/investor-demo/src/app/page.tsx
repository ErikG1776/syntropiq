"use client";

import { useRouter } from "next/navigation";
import { Activity, ShieldAlert, ShieldOff, SlidersHorizontal } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const features = [
  {
    title: "Drift Detection",
    description:
      "Detects trust degradation and behavioral drift in real time across active agent pools.",
    icon: ShieldAlert,
  },
  {
    title: "Agent Suppression",
    description:
      "Autonomously suppresses unstable agents to protect execution quality during stress windows.",
    icon: ShieldOff,
  },
  {
    title: "Adaptive Thresholds",
    description:
      "Adjusts trust and suppression thresholds with deterministic governance controls.",
    icon: SlidersHorizontal,
  },
];

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-[#0b1120] text-zinc-100">
      <div className="mx-auto max-w-6xl px-8 py-10">
        <header className="flex items-center justify-between border-b border-white/10 pb-6">
          <div className="flex items-center gap-2 text-lg font-semibold tracking-tight">
            <Activity className="h-5 w-5 text-zinc-300" />
            <span>Syntropiq</span>
          </div>
          <Badge variant="accent">Governance Control Plane</Badge>
        </header>

        <main className="py-20">
          <section className="mx-auto max-w-3xl text-center">
            <h1 className="text-5xl font-semibold tracking-tight">Autonomous AI. Governed.</h1>
            <p className="mt-5 text-lg text-zinc-400">
              Real-time drift detection, suppression, and adaptive threshold mutation across enterprise AI agents.
            </p>
            <div className="mt-8">
              <Button onClick={() => router.push("/demo")}>Launch Live Demo</Button>
            </div>
          </section>

          <section className="mt-16 grid grid-cols-1 gap-6 md:grid-cols-3">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <Card
                  key={feature.title}
                  className="border border-white/10 bg-[#0f172a] transition-colors hover:border-white/20"
                >
                  <CardHeader>
                    <div className="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-md border border-white/10 bg-[#0b1120]">
                      <Icon className="h-4 w-4 text-blue-500" />
                    </div>
                    <CardTitle className="text-base tracking-normal normal-case text-white">
                      {feature.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm leading-relaxed text-zinc-400">{feature.description}</p>
                  </CardContent>
                </Card>
              );
            })}
          </section>
        </main>
      </div>
    </div>
  );
}
