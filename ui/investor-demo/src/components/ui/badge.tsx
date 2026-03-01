import { cn } from "@/lib/utils";
import { type HTMLAttributes } from "react";

type BadgeVariant = "default" | "success" | "danger" | "warning" | "accent";

const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-white/5 text-text-secondary border-border",
  success: "bg-success-dim text-success border-success/20",
  danger: "bg-danger-dim text-danger border-danger/20",
  warning: "bg-warning-dim text-warning border-warning/20",
  accent: "bg-accent-dim text-accent border-accent/20",
};

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border",
        variantStyles[variant],
        className
      )}
      {...props}
    />
  );
}
