import * as React from "react";
import { cn } from "@/lib/utils";

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-11 w-full rounded-sm border border-white/14 bg-[rgba(5,10,19,0.72)] px-3 py-2 text-sm text-slate-100 placeholder:text-slate-400/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan/70 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
