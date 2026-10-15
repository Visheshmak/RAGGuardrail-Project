import React from "react";
import { X, CheckCircle2, XCircle, FileText, Cpu, ShieldAlert, Sparkles } from "lucide-react";
import { EvaluationCaseResultItem } from "@/types";
import { SeverityBadge } from "./ui/Badge";
import { clsx } from "clsx";

interface TestCaseModalProps {
  caseResult: EvaluationCaseResultItem | null;
  onClose: () => void;
}

export function TestCaseModal({ caseResult, onClose }: TestCaseModalProps) {
  if (!caseResult) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl max-h-[90vh] bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800/80 bg-slate-900/50">
          <div className="flex items-center gap-3">
            <div
              className={clsx(
                "w-8 h-8 rounded-lg flex items-center justify-center border",
                caseResult.passed
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                  : "bg-rose-500/10 text-rose-400 border-rose-500/20"
              )}
            >
              {caseResult.passed ? (
                <CheckCircle2 className="h-4 w-4" />
              ) : (
                <XCircle className="h-4 w-4" />
              )}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-100">Test Case Inspection</h3>
              <p className="text-[11px] text-slate-400 font-mono">
                Latency: {caseResult.latency_ms}ms • Status: {caseResult.passed ? "PASSED" : "FAILED"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Modal Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Question */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              User Prompt / Question
            </label>
            <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-sm text-slate-100 leading-relaxed">
              {caseResult.question}
            </div>
          </div>

          {/* Actual vs Expected Answer */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5" /> Generated RAG Answer
              </label>
              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-200 leading-relaxed min-h-[100px] whitespace-pre-wrap">
                {caseResult.actual_answer || "No answer generated"}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5" /> Expected Golden Answer
              </label>
              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-300 leading-relaxed min-h-[100px] whitespace-pre-wrap">
                {caseResult.expected_answer || "Open-ended (No ground truth specified)"}
              </div>
            </div>
          </div>

          {/* Per-Case Metrics Bar */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Evaluation Metrics
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {Object.entries(caseResult.metrics || {}).map(([key, val]) => (
                <div key={key} className="p-3 rounded-lg bg-slate-950/40 border border-slate-800">
                  <span className="text-[10px] text-slate-400 uppercase font-medium block truncate">
                    {key.replace("_", " ")}
                  </span>
                  <span className="text-base font-bold font-mono text-slate-200">
                    {(val * 100).toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Retrieved Context Chunks */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <FileText className="h-3.5 w-3.5 text-indigo-400" /> Retrieved Context Chunks (
              {caseResult.retrieved_chunks?.length || 0})
            </label>
            <div className="space-y-2.5">
              {caseResult.retrieved_chunks && caseResult.retrieved_chunks.length > 0 ? (
                caseResult.retrieved_chunks.map((chunk, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-slate-950/40 border border-slate-800 text-xs text-slate-300 leading-relaxed"
                  >
                    <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono mb-1.5 pb-1 border-b border-slate-800/60">
                      <span>Source: {chunk.document || "Document"}</span>
                      {chunk.score && <span>Relevance: {(chunk.score * 100).toFixed(1)}%</span>}
                    </div>
                    <p className="line-clamp-4">{chunk.text}</p>
                  </div>
                ))
              ) : (
                <p className="text-xs text-slate-500 italic">No context chunks retrieved.</p>
              )}
            </div>
          </div>

          {/* Guardrails Breakdown */}
          {caseResult.guardrail_results && caseResult.guardrail_results.length > 0 && (
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <ShieldAlert className="h-3.5 w-3.5 text-amber-400" /> Guardrails Evaluation
              </label>
              <div className="space-y-2">
                {caseResult.guardrail_results.map((g, idx) => (
                  <div
                    key={idx}
                    className={clsx(
                      "p-3 rounded-lg border text-xs flex items-start justify-between gap-3",
                      g.passed
                        ? "bg-slate-950/30 border-slate-800/80 text-slate-300"
                        : "bg-rose-950/20 border-rose-800/40 text-rose-300"
                    )}
                  >
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-slate-200 capitalize">
                          {g.guardrail.replace("_", " ")}
                        </span>
                        <SeverityBadge severity={g.severity} />
                      </div>
                      <p className="text-[11px] text-slate-400">{g.reason}</p>
                    </div>
                    <span
                      className={clsx(
                        "text-[10px] font-bold px-2 py-0.5 rounded uppercase shrink-0 font-mono",
                        g.passed ? "text-emerald-400 bg-emerald-950/40" : "text-rose-400 bg-rose-950/40"
                      )}
                    >
                      {g.passed ? "PASSED" : "VIOLATION"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-800/80 bg-slate-900/50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
