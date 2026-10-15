import { clsx } from "clsx";

export function ReleaseDecisionBadge({ decision }: { decision?: string | null }) {
  if (!decision) return null;
  const d = decision.toUpperCase();

  if (d === "PASS") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
        PASS
      </span>
    );
  }

  if (d === "WARNING") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
        WARNING
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
      <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
      BLOCK
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const s = status.toUpperCase();

  const styles: Record<string, string> = {
    COMPLETED: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    RUNNING: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20 animate-pulse",
    PROCESSING: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20 animate-pulse",
    QUEUED: "bg-slate-500/10 text-slate-400 border-slate-500/20",
    PENDING: "bg-slate-500/10 text-slate-400 border-slate-500/20",
    FAILED: "bg-rose-500/10 text-rose-400 border-rose-500/20",
    BLOCK: "bg-rose-500/10 text-rose-400 border-rose-500/20",
    PASS: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    WARNING: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  };

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border",
        styles[s] || styles.QUEUED
      )}
    >
      {s}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const sev = severity.toLowerCase();

  const styles: Record<string, string> = {
    critical: "bg-rose-950/50 text-rose-400 border-rose-800/40",
    high: "bg-rose-500/10 text-rose-400 border-rose-500/20",
    medium: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    low: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  };

  return (
    <span
      className={clsx(
        "inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold uppercase tracking-wider border",
        styles[sev] || styles.low
      )}
    >
      {severity}
    </span>
  );
}
