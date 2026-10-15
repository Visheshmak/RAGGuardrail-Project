import React from "react";
import { ArrowUpRight, ArrowDownRight, Minus, AlertTriangle, CheckCircle2 } from "lucide-react";
import { clsx } from "clsx";

interface MetricCardProps {
  title: string;
  value: number | string | null | undefined;
  baselineValue?: number | null;
  minimumRequired?: number | null;
  unit?: string;
  status?: "PASS" | "WARNING" | "FAIL" | string;
  subtitle?: string;
  isPercentage?: boolean;
}

export function MetricCard({
  title,
  value,
  baselineValue,
  minimumRequired,
  unit = "",
  status,
  subtitle,
  isPercentage = true,
}: MetricCardProps) {
  const numericValue = typeof value === "number" ? value : null;
  const formattedValue =
    numericValue !== null
      ? isPercentage
        ? `${(numericValue * 100).toFixed(1)}%`
        : `${numericValue.toFixed(2)}${unit}`
      : value ?? "—";

  let diff: number | null = null;
  if (numericValue !== null && baselineValue !== undefined && baselineValue !== null) {
    diff = numericValue - baselineValue;
  }

  const isPositive = diff !== null && diff > 0.001;
  const isNegative = diff !== null && diff < -0.001;
  const isNeutral = diff !== null && Math.abs(diff) <= 0.001;

  const isFailed = status === "FAIL" || (minimumRequired !== undefined && minimumRequired !== null && numericValue !== null && numericValue < minimumRequired);
  const isWarning = status === "WARNING";

  return (
    <div
      className={clsx(
        "p-5 rounded-xl border bg-slate-900/60 backdrop-blur-sm relative overflow-hidden transition-all",
        isFailed
          ? "border-rose-500/40 bg-rose-950/10 shadow-sm shadow-rose-950/50"
          : isWarning
          ? "border-amber-500/40 bg-amber-950/10"
          : "border-slate-800/80 hover:border-slate-700/80"
      )}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider truncate">
          {title}
        </span>
        {status && (
          <span
            className={clsx(
              "px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider",
              isFailed
                ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                : isWarning
                ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
            )}
          >
            {status}
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-2 mb-2">
        <span className="text-2xl font-bold tracking-tight text-white font-mono">
          {formattedValue}
        </span>

        {diff !== null && (
          <span
            className={clsx(
              "inline-flex items-center text-xs font-mono font-medium",
              isPositive ? "text-emerald-400" : isNegative ? "text-rose-400" : "text-slate-400"
            )}
          >
            {isPositive && <ArrowUpRight className="h-3.5 w-3.5 mr-0.5" />}
            {isNegative && <ArrowDownRight className="h-3.5 w-3.5 mr-0.5" />}
            {isNeutral && <Minus className="h-3.5 w-3.5 mr-0.5" />}
            {diff > 0 ? "+" : ""}
            {isPercentage ? `${(diff * 100).toFixed(1)}%` : diff.toFixed(2)}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-800/60">
        <div>
          {baselineValue !== undefined && baselineValue !== null ? (
            <span>
              Baseline:{" "}
              <strong className="text-slate-400 font-mono">
                {isPercentage ? `${(baselineValue * 100).toFixed(1)}%` : `${baselineValue.toFixed(2)}`}
              </strong>
            </span>
          ) : (
            <span>{subtitle || "No baseline set"}</span>
          )}
        </div>

        {minimumRequired !== undefined && minimumRequired !== null && (
          <span>
            Min:{" "}
            <strong className="text-slate-400 font-mono">
              {isPercentage ? `${(minimumRequired * 100).toFixed(1)}%` : minimumRequired}
            </strong>
          </span>
        )}
      </div>
    </div>
  );
}
