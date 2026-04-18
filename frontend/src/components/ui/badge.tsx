import type { HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex rounded-sm border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] telemetry-value",
  {
    variants: {
      variant: {
        low: "border-neon-cyan/45 bg-neon-cyan/12 text-neon-cyan",
        moderate: "border-neon-amber/45 bg-neon-amber/14 text-neon-amber",
        high: "border-neon-coral/50 bg-neon-coral/14 text-neon-coral",
        critical: "border-red-400/55 bg-red-500/22 text-red-100",
        neutral: "border-white/15 bg-white/8 text-slate-200"
      }
    },
    defaultVariants: {
      variant: "neutral"
    }
  }
);

type BadgeProps = HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>;

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
