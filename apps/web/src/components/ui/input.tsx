import { cn } from "@/lib/utils";
import { type InputHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={cn(
          "w-full px-3 py-2 rounded-lg border border-border bg-navy-800 text-slate-100",
          "placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan focus:border-transparent",
          "transition-all",
          error && "border-red-500 focus:ring-red-500",
          className,
        )}
        {...props}
      />
    );
  },
);

Input.displayName = "Input";

export function Label({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={cn("block text-sm font-medium text-slate-300 mb-1.5", className)}
      {...props}
    />
  );
}

export function ErrorMessage({ children }: { children: React.ReactNode }) {
  return <p className="mt-1 text-sm text-red-400">{children}</p>;
}
