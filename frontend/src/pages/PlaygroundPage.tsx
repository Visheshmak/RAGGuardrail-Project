import React, { useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/services/api";
import { QueryResponseItem } from "@/types";
import { ProjectTabs } from "@/components/ui/ProjectTabs";
import { SeverityBadge } from "@/components/ui/Badge";
import {
  Terminal,
  Send,
  Sparkles,
  FileText,
  ShieldCheck,
  ShieldAlert,
  Clock,
  Cpu,
  Layers,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { clsx } from "clsx";

export function PlaygroundPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(4);
  const [similarityThreshold, setSimilarityThreshold] = useState(0.0);
  const [enableGuardrails, setEnableGuardrails] = useState(true);
  const [response, setResponse] = useState<QueryResponseItem | null>(null);

  const queryMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post(`/api/v1/projects/${projectId}/query`, {
        question: question.trim(),
        top_k: topK,
        similarity_threshold: similarityThreshold,
        enable_guardrails: enableGuardrails,
      });
      return res.data;
    },
    onSuccess: (data) => {
      setResponse(data);
    },
  });

  const handleQuery = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    queryMutation.mutate();
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">RAG Sandbox & Guardrail Playground</h1>
          <p className="text-xs text-slate-400 mt-1">
            Test live question retrieval against your project documentation and inspect real-time safety gating.
          </p>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <ProjectTabs projectId={projectId!} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Query Form & Controls */}
        <div className="space-y-4">
          <form onSubmit={handleQuery} className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-300">
              <Terminal className="h-4 w-4 text-indigo-400" />
              <span>Prompt Query</span>
            </div>

            <div>
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask a question about your project documentation..."
                rows={4}
                className="w-full p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none leading-relaxed"
              />
            </div>

            {/* Hyperparameters */}
            <div className="space-y-3 pt-2 border-t border-slate-800/60 text-xs">
              <div>
                <div className="flex justify-between text-slate-400 mb-1">
                  <span>Top K Retrieval:</span>
                  <span className="font-mono text-slate-200">{topK}</span>
                </div>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  className="w-full accent-indigo-500 cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-slate-400 mb-1">
                  <span>Similarity Cutoff:</span>
                  <span className="font-mono text-slate-200">{similarityThreshold.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min={0.0}
                  max={0.9}
                  step={0.05}
                  value={similarityThreshold}
                  onChange={(e) => setSimilarityThreshold(Number(e.target.value))}
                  className="w-full accent-indigo-500 cursor-pointer"
                />
              </div>

              <div className="flex items-center justify-between pt-1">
                <span className="text-slate-400">Enforce Guardrails:</span>
                <input
                  type="checkbox"
                  checked={enableGuardrails}
                  onChange={(e) => setEnableGuardrails(e.target.checked)}
                  className="h-4 w-4 rounded accent-indigo-600 bg-slate-900 border-slate-700 cursor-pointer"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={!question.trim() || queryMutation.isPending}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold rounded-xl shadow-md shadow-indigo-600/25 transition-colors cursor-pointer flex items-center justify-center gap-2"
            >
              <Send className="h-3.5 w-3.5" />
              {queryMutation.isPending ? "Generating Answer..." : "Submit Query"}
            </button>
          </form>
        </div>

        {/* Right Column: Output & Citations (2 Cols) */}
        <div className="lg:col-span-2 space-y-4">
          {queryMutation.isPending && (
            <div className="p-12 rounded-xl border border-slate-800 bg-slate-900/40 text-center text-xs text-slate-400 space-y-2">
              <Sparkles className="h-6 w-6 text-indigo-400 animate-spin mx-auto" />
              <p>Searching Qdrant vector database and evaluating guardrail policies...</p>
            </div>
          )}

          {response && !queryMutation.isPending && (
            <div className="space-y-4">
              {/* Answer Card */}
              <div
                className={clsx(
                  "p-5 rounded-xl border backdrop-blur-sm space-y-3",
                  response.blocked
                    ? "bg-rose-950/15 border-rose-800/50"
                    : "bg-slate-900/80 border-slate-800"
                )}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-indigo-400" />
                    <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                      Generated Response
                    </h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-mono text-slate-400">
                      Latency: {response.latency_ms}ms • Model: {response.model}
                    </span>
                    {response.blocked ? (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">
                        BLOCKED
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                        ALLOW
                      </span>
                    )}
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs text-slate-100 leading-relaxed whitespace-pre-wrap font-sans">
                  {response.answer}
                </div>
              </div>

              {/* Guardrails Breakdown */}
              {response.guardrail_results && response.guardrail_results.length > 0 && (
                <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 space-y-3">
                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    <ShieldCheck className="h-4 w-4 text-emerald-400" />
                    <span>Real-Time Guardrail Inspection</span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {response.guardrail_results.map((g, idx) => (
                      <div
                        key={idx}
                        className={clsx(
                          "p-2.5 rounded-lg border text-xs flex items-center justify-between gap-2",
                          g.passed
                            ? "bg-slate-950/40 border-slate-800 text-slate-300"
                            : "bg-rose-950/20 border-rose-800/40 text-rose-300"
                        )}
                      >
                        <div className="min-w-0 truncate">
                          <span className="font-semibold block truncate capitalize">
                            {g.guardrail.replace("_", " ")}
                          </span>
                          <span className="text-[10px] text-slate-500 block truncate">{g.reason}</span>
                        </div>
                        <SeverityBadge severity={g.severity} />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Source Citations */}
              <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 space-y-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  <FileText className="h-4 w-4 text-indigo-400" />
                  <span>Retrieved Context Snippets ({response.sources.length})</span>
                </div>

                <div className="space-y-2.5">
                  {response.sources.length > 0 ? (
                    response.sources.map((src, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-xs space-y-1.5"
                      >
                        <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pb-1 border-b border-slate-800/60">
                          <span className="font-semibold text-slate-300 truncate">
                            {src.document} {src.page ? `(Page ${src.page})` : ""}
                          </span>
                          <span className="text-indigo-400">Score: {(src.score * 100).toFixed(1)}%</span>
                        </div>
                        <p className="text-slate-300 leading-relaxed font-sans">{src.text}</p>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-slate-500 italic py-2">No relevant source context retrieved.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {!response && !queryMutation.isPending && (
            <div className="p-16 rounded-xl border border-dashed border-slate-800 bg-slate-900/20 text-center text-xs text-slate-500">
              Submit a prompt query on the left to see live retrieved context chunks and safety telemetry.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
