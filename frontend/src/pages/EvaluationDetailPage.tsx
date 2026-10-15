import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";
import {
  EvaluationRunItem,
  EvaluationCaseResultItem,
  ReleaseDecisionItem,
  BaselineItem,
} from "@/types";
import { ProjectTabs } from "@/components/ui/ProjectTabs";
import { ReleaseDecisionBadge, StatusBadge, SeverityBadge } from "@/components/ui/Badge";
import { TestCaseModal } from "@/components/TestCaseModal";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/States";
import {
  Activity,
  ShieldCheck,
  ShieldAlert,
  ArrowLeft,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Cpu,
  Database,
  Layers,
  Sparkles,
  ExternalLink,
} from "lucide-react";
import { clsx } from "clsx";

export function EvaluationDetailPage() {
  const { projectId, evaluationId } = useParams<{ projectId: string; evaluationId: string }>();
  const queryClient = useQueryClient();
  const [selectedCase, setSelectedCase] = useState<EvaluationCaseResultItem | null>(null);
  const [baselineNotes, setBaselineNotes] = useState("");
  const [showPromoteModal, setShowPromoteModal] = useState(false);

  // 1. Fetch Evaluation Run with polling if RUNNING or QUEUED
  const {
    data: run,
    isLoading: runLoading,
    isError: runError,
    refetch,
  } = useQuery<EvaluationRunItem>({
    queryKey: ["evaluation-run", projectId, evaluationId],
    queryFn: async () => {
      const res = await api.get(`/api/v1/projects/${projectId}/evaluations/${evaluationId}`);
      return res.data;
    },
    enabled: !!projectId && !!evaluationId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "RUNNING" || status === "PENDING" ? 2000 : false;
    },
  });

  // 2. Fetch Release Decision & Regression Comparison
  const { data: releaseDecision } = useQuery<ReleaseDecisionItem>({
    queryKey: ["release-decision", projectId, evaluationId],
    queryFn: async () => {
      const res = await api.get(`/api/v1/projects/${projectId}/evaluations/${evaluationId}/release-decision`);
      return res.data;
    },
    enabled: !!projectId && !!evaluationId && run?.status === "COMPLETED",
  });

  // 3. Fetch Baselines to check if this run is already active baseline
  const { data: baselines = [] } = useQuery<BaselineItem[]>({
    queryKey: ["project-baselines", projectId],
    queryFn: async () => {
      const res = await api.get(`/api/v1/projects/${projectId}/baselines`);
      return res.data;
    },
    enabled: !!projectId,
  });
  const isActiveBaseline = baselines.some((b) => b.evaluation_run_id === evaluationId && b.is_active);

  // 4. Mutation to Promote as Active Baseline
  const promoteMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post(`/api/v1/projects/${projectId}/baselines`, {
        evaluation_run_id: evaluationId,
        notes: baselineNotes || `Baseline promoted from run ${run?.name}`,
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-baselines", projectId] });
      queryClient.invalidateQueries({ queryKey: ["release-decision", projectId, evaluationId] });
      setShowPromoteModal(false);
      setBaselineNotes("");
    },
  });

  if (runLoading) {
    return <LoadingState message="Fetching evaluation run and regression analytics..." />;
  }

  if (runError || !run) {
    return <ErrorState message="Evaluation run not found." onRetry={refetch} />;
  }

  const metrics = run.metrics || {};
  const config = run.configuration_snapshot || {};
  const guardrails = run.guardrail_summary || {};
  const comparisons = releaseDecision?.metrics_comparison || [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Back Link & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <Link
            to={`/projects/${projectId}/evaluations`}
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 mb-2 transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back to Evaluations
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">{run.name}</h1>
            <StatusBadge status={run.status} />
            {releaseDecision && <ReleaseDecisionBadge decision={releaseDecision.decision} />}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Executed on {new Date(run.created_at).toLocaleString()} • ID: {run.id}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {isActiveBaseline ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold">
              <ShieldCheck className="h-4 w-4" /> Active Project Baseline
            </span>
          ) : (
            <button
              onClick={() => setShowPromoteModal(true)}
              disabled={run.status !== "COMPLETED"}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md shadow-indigo-600/25 transition-colors cursor-pointer"
            >
              <ShieldCheck className="h-4 w-4" />
              Promote as Baseline
            </button>
          )}
        </div>
      </div>

      {/* Sub-Tabs Navigation */}
      <ProjectTabs projectId={projectId!} />

      {/* Release Decision Callout if Blocked or Warning */}
      {releaseDecision && releaseDecision.decision === "BLOCK" && (
        <div className="p-4 rounded-xl bg-rose-950/20 border border-rose-800/50 flex items-start gap-3 text-rose-300 text-xs leading-relaxed">
          <XCircle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-rose-200 text-sm">Release Gating: BLOCKED</h4>
            <p className="mt-1 text-rose-300">
              This candidate evaluation has violated regression safety constraints and is blocked from deployment.
            </p>
            <ul className="list-disc list-inside mt-2 space-y-1 font-mono text-[11px]">
              {releaseDecision.reasons.map((r, idx) => (
                <li key={idx}>{r.reason || `${r.metric}: regression exceeds allowed limit`}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {releaseDecision && releaseDecision.decision === "PASS" && (
        <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-800/50 flex items-center gap-3 text-emerald-300 text-xs">
          <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
          <div>
            <h4 className="font-semibold text-emerald-200 text-sm">Release Gating: APPROVED (PASS)</h4>
            <p className="mt-0.5 text-emerald-300">
              Candidate passed all regression tolerances, minimum thresholds, and guardrail checks against the baseline.
            </p>
          </div>
        </div>
      )}

      {/* Overview Cards (Run Config & Telemetry) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Run Specs Card */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-3">
          <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <Cpu className="h-4 w-4 text-indigo-400" />
            <span>Execution Environment</span>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">LLM Model:</span>
              <span className="font-mono text-slate-200">{config.model || "gpt-4o-mini"}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Embedding:</span>
              <span className="font-mono text-slate-200">{config.embedding_model || "text-embedding-3-small"}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-400">Top K Chunks:</span>
              <span className="font-mono text-slate-200">{config.top_k || 5}</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Cases Evaluated:</span>
              <span className="font-mono text-slate-200">
                {run.completed_cases} / {run.total_cases}
              </span>
            </div>
          </div>
        </div>

        {/* Overall Score Card */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm flex flex-col justify-between">
          <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <Sparkles className="h-4 w-4 text-indigo-400" />
            <span>Aggregate Quality Score</span>
          </div>
          <div className="py-3">
            <span className="text-4xl font-bold font-mono text-white">
              {typeof metrics.accuracy === "number" ? `${(metrics.accuracy * 100).toFixed(1)}%` : "—"}
            </span>
            <p className="text-xs text-slate-400 mt-1">Average correctness across evaluated test cases</p>
          </div>
          <div className="text-[11px] text-slate-500 font-mono flex items-center justify-between border-t border-slate-800/60 pt-2">
            <span>Latency: {metrics.latency_ms ? `${metrics.latency_ms}ms` : "—"}</span>
            <span>Safety: {typeof metrics.safety === "number" ? `${(metrics.safety * 100).toFixed(1)}%` : "—"}</span>
          </div>
        </div>

        {/* Guardrails Summary Card */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-3">
          <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <ShieldAlert className="h-4 w-4 text-amber-400" />
            <span>Guardrails Telemetry</span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center py-1">
            <div className="p-2 rounded-lg bg-slate-950/40 border border-slate-800/80">
              <span className="text-[10px] text-slate-400 block">Total</span>
              <span className="text-lg font-bold font-mono text-slate-200">
                {guardrails.total_violations ?? 0}
              </span>
            </div>
            <div className="p-2 rounded-lg bg-slate-950/40 border border-slate-800/80">
              <span className="text-[10px] text-slate-400 block">Critical</span>
              <span className="text-lg font-bold font-mono text-rose-400">
                {guardrails.critical_violations ?? 0}
              </span>
            </div>
            <div className="p-2 rounded-lg bg-slate-950/40 border border-slate-800/80">
              <span className="text-[10px] text-slate-400 block">High</span>
              <span className="text-lg font-bold font-mono text-amber-400">
                {guardrails.high_violations ?? 0}
              </span>
            </div>
          </div>
          <p className="text-[11px] text-slate-400 text-center">
            {(guardrails.critical_violations ?? 0) === 0
              ? "No critical guardrail breaches detected."
              : "Critical safety violations require immediate review."}
          </p>
        </div>
      </div>

      {/* Regression & Metrics Comparison Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
        <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white">Regression Comparison Table</h3>
            <p className="text-xs text-slate-400">
              Comparing Candidate Run against Baseline v{releaseDecision?.baseline_version ?? 1}
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Metric</th>
                <th className="py-3 px-4">Current Score</th>
                <th className="py-3 px-4">Baseline Score</th>
                <th className="py-3 px-4">Regression (Drop)</th>
                <th className="py-3 px-4">Allowed Regression</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Diagnostic Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {comparisons.length > 0 ? (
                comparisons.map((c) => {
                  const isFail = c.status === "FAIL";
                  const isWarn = c.status === "WARNING";
                  return (
                    <tr
                      key={c.metric}
                      className={clsx(
                        "hover:bg-slate-800/30 transition-colors",
                        isFail && "bg-rose-950/10"
                      )}
                    >
                      <td className="py-3 px-4 font-sans font-semibold text-slate-200 capitalize">
                        {c.metric.replace("_", " ")}
                      </td>
                      <td className="py-3 px-4 font-bold text-white">
                        {(c.current * 100).toFixed(1)}%
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {(c.baseline * 100).toFixed(1)}%
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={clsx(
                            c.actual_regression > c.allowed_regression
                              ? "text-rose-400 font-bold"
                              : "text-slate-300"
                          )}
                        >
                          {(c.actual_regression * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {(c.allowed_regression * 100).toFixed(1)}%
                      </td>
                      <td className="py-3 px-4 font-sans">
                        <span
                          className={clsx(
                            "px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider",
                            isFail
                              ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                              : isWarn
                              ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                              : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                          )}
                        >
                          {c.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-sans text-slate-400 text-[11px]">
                        {c.reason || "Within expected safety bounds"}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-slate-500 font-sans text-xs">
                    Promote a baseline to enable automatic regression tracking and differential analysis.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Baseline Promotion Confirmation Modal */}
      {showPromoteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">Promote as Active Baseline</h3>
                <p className="text-xs text-slate-400">Sets this run as the new standard for regression gating.</p>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Baseline Version Notes</label>
              <textarea
                value={baselineNotes}
                onChange={(e) => setBaselineNotes(e.target.value)}
                placeholder="e.g. Q4 Gold Standard with updated chunking..."
                className="w-full h-24 p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
              />
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                onClick={() => setShowPromoteModal(false)}
                className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 rounded-lg transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => promoteMutation.mutate()}
                disabled={promoteMutation.isPending}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg shadow-md shadow-indigo-600/25 transition-colors cursor-pointer"
              >
                {promoteMutation.isPending ? "Promoting..." : "Confirm Promotion"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Test Case Inspection Modal */}
      <TestCaseModal caseResult={selectedCase} onClose={() => setSelectedCase(null)} />
    </div>
  );
}
