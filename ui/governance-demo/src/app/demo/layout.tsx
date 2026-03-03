"use client";

import { ControlShell } from "@/components/control/control-shell";
import { ControlPlaneProvider } from "@/lib/control-plane-context";

export default function ControlLayout({ children }: { children: React.ReactNode }) {
  return (
    <ControlPlaneProvider>
      <ControlShell>{children}</ControlShell>
    </ControlPlaneProvider>
  );
}
