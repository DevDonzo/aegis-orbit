import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-sm border text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan/70 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "border-neon-cyan/55 bg-[linear-gradient(135deg,rgba(99,245,228,0.22),rgba(138,182,255,0.12))] text-slate-50 hover:border-neon-cyan/80 hover:bg-[linear-gradient(135deg,rgba(99,245,228,0.3),rgba(138,182,255,0.18))]",
        secondary: "border-white/14 bg-white/6 text-slate-100 hover:border-white/22 hover:bg-white/10",
        ghost: "border-transparent bg-transparent text-slate-100 hover:border-white/10 hover:bg-white/8",
        destructive: "border-neon-coral/60 bg-neon-coral/14 text-slate-50 hover:bg-neon-coral/24"
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 px-3",
        lg: "h-11 px-8"
      }
    },
    defaultVariants: {
      variant: "default",
      size: "default"
    }
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return <button className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
