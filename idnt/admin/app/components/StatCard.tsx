"use client";

interface StatCardProps {
  value: number;
  label: string;
  variant?: "default" | "accent" | "error";
}

export default function StatCard({ value, label, variant = "default" }: StatCardProps) {
  const colorMap = {
    default: "text-white",
    accent: "text-accent",
    error: value > 0 ? "text-error" : "text-muted",
  };

  return (
    <div className="group rounded-2xl border border-white/[0.06] bg-white/[0.02] px-8 py-7 transition-all duration-200 hover:border-white/[0.1] hover:bg-white/[0.04]">
      <p className={`tabular-nums text-5xl font-bold tracking-tight ${colorMap[variant]}`}>
        {value}
      </p>
      <p className="mt-2 text-sm text-muted">{label}</p>
    </div>
  );
}
