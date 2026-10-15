import React from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/services/api";
import { Project, BaselineItem, EvaluationRunItem, ReleaseDecisionItem, ProjectThresholdConfigItem } from "@/types";
import { ProjectTabs } from "@/components/ui/ProjectTabs";
import { MetricCard } from "@/components/ui/MetricCard";
import { ReleaseDecisionBadge, StatusBadge } from "@/components/ui/Badge";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/States";
import {
  Sparkles,
  ShieldCheck,
  Activity,
  ArrowRight,
  Plus,
  Play,
  Calendar,
  Layers,
  CheckCircle2,
} from "lucide-react";

export function ProjectOverviewPage() {
  const { projectId } = useParams<{ projectId: string }>();

  // Fetch project details
  const {
    data: project,
    isLoading: projectLoading,
    isError: projectError,
    refetch,
  } = useQuery<Project>({
    queryKey: ["project", projectId],
    queryFn: async () => {
      const res = await api.get(`/api/v1/projects/${projectId}`);
      return res.data;
    },
    enabled: !!projectId,
  });

  // Fetch active baseline
  const { data: baselines = [] } = useQuery<BaselineItem[]>({
    queryKey: ["project-baselines", projectId],
    queryFn: async () => {
      const res = await api.get(`/api/v1/projects/${projectId}/baselines`);
      return res.data;
    },
    enabled: !!projectId,
  });
  const activeBaseline = baselines.find((b) => b.is_active);

  // Fetch latest evaluation run
  const { data: runs = [] } = useQuery<EvaluationRunItem[]>({
    queryKey: ["project-evaluations", projectId],
    queryFn: async () => {
      const res = await api.get(`/api/v1/projects/${projectId}/evaluations?limit=10`);
      return res.data;
    },
    enabled: !!projectId,
  });
  const latestRun = runs[0];

  // Fetch release decision for latest run against active baseline
  const { data: releaseDecision } = useQuery<ReleaseDecisionItem>({
    queryKey: ["latest-release-decision", projectId, latestRun?.id],
    queryFn: async () => {
      if (!latestRun) return null;
      const res = await api.get(`/api/v1/projects/${projectId}/evaluations/${latestRun.id}/release-decision`);
      return res.data;
    },
    enabled: !!projectId && !!latestRun && !!activeBaseline,
  });

  // Fetch project threshold config
  const { data: thresholdConfig } = useQuery<ProjectThresholdConfigItem>({
    queryKey: ["project-thresholds", projectId],
    queryFn: async () => {
      const res = await api.get(`/api/v1/projects/${projectId}/thresholds`);
      return res.data;
    },
    enabled: !!projectId,
  });

  if (projectLoading) {
    return <LoadingState message="Loading project overview..." />;
  }

  if (projectError || !project) {
    return <ErrorState message="Project could not be found or loaded." onRetry={refetch} />;
  }

  const latestMetrics = latestRun?.metrics || {};
  const baselineMetrics = activeBaseline?.metrics_snapshot || {};
  const thresholds = thresholdConfig?.thresholds || {};

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Project Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">{project.name}</h1>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
              ID: {project.id.substring(0, 8)}...
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {project.description || "Regression-safe RAG pipeline evaluation & guardrails monitoring."}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            to={`/projects/${projectId}/playground`}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
          >
            <Play className="h-3.5 w-3.5 text-indigo-400" />
            RAG Sandbox
          </Link>
          <Link
            to={`/projects/${projectId}/evaluations`}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/25 transition-colors"
          >
            <Activity className="h-3.5 w-3.5" />
            Evaluation Hub
          </Link>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <ProjectTabs projectId={projectId!} />

      {/* Top Status Banners: Active Baseline & Release Gate Decision */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Active Baseline Card */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm relative overflow-hidden">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-indigo-400" />
              <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Current Active Baseline
              </h3>
            </div>
            {activeBaseline && (
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                v{activeBaseline.version}
              </span>
            )}
          </div>

          {activeBaseline ? (
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="p-2 rounded-lg bg-slate-950/40 border border-slate-800/80">
                  <span className="text-[10px] text-slate-400 uppercase block">Accuracy</span>
                  <span className="text-base font-bold font-mono text-slate-200">
                    {((activeBaseline.metrics_snapshot.accuracy || 0) * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-slate-950/40 border border-slate-800/80">
                  <span className="text-[10px] text-slate-400 uppercase block">Faithfulness</span>
                  <span className="text-base font-bold font-mono text-emerald-400">
                    {((activeBaseline.metrics_snapshot.faithfulness || 0) * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-slate-950/40 border border-slate-800/80">
                  <span className="text-[10px] text-slate-400 uppercase block">Recall</span>
                  <span className="text-base font-bold font-mono text-cyan-400">
                    {((activeBaseline.metrics_snapshot.retrieval_recall || 0) * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
              <div className="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-800/60">
                <span>Created: {new Date(activeBaseline.created_at).toLocaleDateString()}</span>
                <span className="text-slate-400 truncate max-w-[160px]">{activeBaseline.notes || "Standard Baseline"}</span>
              </div>
            </div>
          ) : (
            <div className="py-4 text-center">
              <p className="text-xs text-slate-400 mb-2">No active baseline promoted yet.</p>
              <p className="text-[11px] text-slate-500">Run an evaluation and promote it as your golden baseline.</p>
            </div>
          )}
        </div>

        {/* Latest Evaluation & Release Gating Banner */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm relative overflow-hidden">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-indigo-400" />
              <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Latest Evaluation & Release Gate
              </h3>
            </div>
            {releaseDecision && <ReleaseDecisionBadge decision={releaseDecision.decision} />}
          </div>

          {latestRun ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-semibold text-white">{latestRun.name}</h4>
                  <p className="text-[11px] text-slate-400 font-mono">
                    Cases: {latestRun.completed_cases}/{latestRun.total_cases} • Status: {latestRun.status}
                  </p>
                </div>
                <Link
                  to={`/projects/${projectId}/evaluations/${latestRun.id}`}
                  className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                >
                  View Details <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>

              {releaseDecision?.reasons && releaseDecision.reasons.length > 0 && (
                <div className="p-2.5 rounded-lg bg-rose-950/20 border border-rose-800/40 text-[11px] text-rose-300">
                  <span className="font-semibold block mb-0.5">Release Blocked:</span>
                  <ul className="list-disc list-inside space-y-0.5">
                    {releaseDecision.reasons.map((r, i) => (
                      <li key={i}>{r.reason || `${r.metric} regression detected`}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="py-4 text-center">
              <p className="text-xs text-slate-400 mb-2">No evaluations executed yet.</p>
              <Link
                to={`/projects/${projectId}/evaluations`}
                className="text-xs text-indigo-400 hover:underline inline-flex items-center gap-1"
              >
                Launch your first evaluation <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Metrics Grid */}
      <div>
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
          Core RAG & Guardrail Metrics (Latest vs Baseline)
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Accuracy / Match"
            value={latestMetrics.accuracy}
            baselineValue={baselineMetrics.accuracy}
            minimumRequired={thresholds.accuracy?.minimum ?? 0.9}
            status={
              typeof latestMetrics.accuracy === "number" && latestMetrics.accuracy < (thresholds.accuracy?.minimum ?? 0.9)
                ? "FAIL"
                : "PASS"
            }
          />
          <MetricCard
            title="Faithfulness / Grounding"
            value={latestMetrics.faithfulness}
            baselineValue={baselineMetrics.faithfulness}
            minimumRequired={thresholds.faithfulness?.minimum ?? 0.9}
            status={
              typeof latestMetrics.faithfulness === "number" &&
              latestMetrics.faithfulness < (thresholds.faithfulness?.minimum ?? 0.9)
                ? "FAIL"
                : "PASS"
            }
          />
          <MetricCard
            title="Retrieval Recall"
            value={latestMetrics.retrieval_recall}
            baselineValue={baselineMetrics.retrieval_recall}
            minimumRequired={thresholds.retrieval_recall?.minimum ?? 0.85}
            status={
              typeof latestMetrics.retrieval_recall === "number" &&
              latestMetrics.retrieval_recall < (thresholds.retrieval_recall?.minimum ?? 0.85)
                ? "FAIL"
                : "PASS"
            }
          />
          <MetricCard
            title="Safety & Guardrails"
            value={latestMetrics.safety}
            baselineValue={baselineMetrics.safety}
            minimumRequired={thresholds.safety?.minimum ?? 0.98}
            status={
              (latestRun?.guardrail_summary?.critical_violations ?? 0) > 0
                ? "FAIL"
                : "PASS"
            }
          />
        </div>
      </div>

      {/* Recent Evaluations History */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
        <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white">Project Evaluation History</h3>
            <p className="text-xs text-slate-400">All evaluation runs and regression status for {project.name}</p>
          </div>
          <Link
            to={`/projects/${projectId}/evaluations`}
            className="text-xs text-indigo-400 hover:text-indigo-300 font-medium hover:underline flex items-center gap-1"
          >
            View All ({runs.length}) <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {runs.length === 0 ? (
          <EmptyState
            title="No evaluation runs yet"
            description="Start by evaluating your RAG pipeline against test cases."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Name</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Accuracy</th>
                  <th className="py-3 px-4">Faithfulness</th>
                  <th className="py-3 px-4">Recall</th>
                  <th className="py-3 px-4">Violations</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {runs.slice(0, 5).map((r) => (
                  <tr key={r.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 font-sans font-medium text-slate-200">{r.name}</td>
                    <td className="py-3 px-4">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="py-3 px-4 text-slate-200">
                      {typeof r.metrics?.accuracy === "number" ? `${(r.metrics.accuracy * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="py-3 px-4 text-slate-200">
                      {typeof r.metrics?.faithfulness === "number" ? `${(r.metrics.faithfulness * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="py-3 px-4 text-slate-200">
                      {typeof r.metrics?.retrieval_recall === "number" ? `${(r.metrics.retrieval_recall * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="py-3 px-4">
                      {(r.guardrail_summary?.total_violations ?? 0) > 0 ? (
                        <span className="text-rose-400 font-bold">{r.guardrail_summary?.total_violations}</span>
                      ) : (
                        <span className="text-emerald-400">0</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-sans">
                      {new Date(r.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 text-right font-sans">
                      <Link
                        to={`/projects/${projectId}/evaluations/${r.id}`}
                        className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300 font-medium hover:underline"
                      >
                        Inspect <ArrowRight className="h-3 w-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
