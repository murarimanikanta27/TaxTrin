import clsx from "clsx";
import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes, LabelHTMLAttributes, SelectHTMLAttributes } from "react";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={clsx("rounded-xl border border-slate-200 bg-white shadow-sm", className)} {...props} />;
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={clsx("border-b border-slate-100 px-5 py-4", className)} {...props} />;
}

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={clsx("text-base font-semibold text-slate-900", className)} {...props} />;
}

export function CardBody({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={clsx("px-5 py-4", className)} {...props} />;
}

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

export function Button({
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  const variants: Record<ButtonVariant, string> = {
    primary: "bg-brand-600 text-white hover:bg-brand-700 disabled:bg-slate-300",
    secondary: "bg-slate-100 text-slate-900 hover:bg-slate-200 disabled:text-slate-400",
    ghost: "bg-transparent text-slate-700 hover:bg-slate-100",
    danger: "bg-red-600 text-white hover:bg-red-700 disabled:bg-red-300",
  };
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={clsx(
        "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500",
        className
      )}
      {...props}
    />
  );
}

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={clsx(
        "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500",
        className
      )}
      {...props}
    />
  );
}

export function Label({ className, ...props }: LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={clsx("mb-1 block text-xs font-medium text-slate-600", className)} {...props} />;
}

export function Badge({
  className,
  tone = "slate",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: "slate" | "green" | "amber" | "red" | "blue" }) {
  const tones: Record<string, string> = {
    slate: "bg-slate-100 text-slate-700",
    green: "bg-emerald-100 text-emerald-700",
    amber: "bg-amber-100 text-amber-700",
    red: "bg-red-100 text-red-700",
    blue: "bg-blue-100 text-blue-700",
  };
  return <span className={clsx("rounded-full px-2.5 py-0.5 text-xs font-medium", tones[tone], className)} {...props} />;
}

export function ErrorText({ message }: { message: string | null }) {
  if (!message) return null;
  return <p className="mt-2 text-sm text-red-600">{message}</p>;
}

export function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <Label>{label}</Label>
      {children}
    </div>
  );
}
