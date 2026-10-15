import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "@/services/api";
import { Project, EvaluationRunItem } from "@/types";
import {
  FolderKanban,
  Activity,
  CheckCircle2,
  XCircle,
  TrendingUp,
  AlertTriangle,
  ShieldAlert,
  Plus,
  ArrowRight,
} from "lucide-react";
import { ReleaseDecisionBadge, StatusBadge } from "@/components/ui/Badge";
import { MetricTrendChart, DataPoint } from "@/components/ui/Chart";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/States";

export function DashboardOverviewPage() {
  // Fetch all projects
  const {
    data: projects = [],
    isLoading: projectsLoading,
    isError: projectsError,
    refetch,
  } = useQuery<Project[]>({
    queryKey: ["projects"],
    queryFn: async () => {
      const res = await api.get("/api/v1/projects");
      return res.data;
    },
  });

  // Fetch recent evaluations across all projects
  const { data: allRuns = [], isLoading: runsLoading } = useQuery<EvaluationRunItem[]>({
    queryKey: ["all-evaluation-runs", projects.map((p) => p.id)],
    queryFn: async () => {
      if (!projects.length) return [];
      const runPromises = projects.map((p) =>
        api
          .get(`/api/v1/projects/${p.id}/evaluations?limit=10`)
          .then((res) => res.data)
          .catch(() => [])
      );
      const results = await Promise.all(runPromises);
      return results.flat().sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    },
    enabled: projects.length > 0,
  });

  if (projectsLoading || runsLoading) {
    return <LoadingState message="Loading platform telemetry and evaluation dashboard..." />;
  }

  if (projectsError) {
    return <ErrorState message="Could not connect to RAGGuard backend API." onRetry={refetch} />;
  }

  // Calculate high-level stats
  const totalProjects = projects.length;
  const totalRuns = allRuns.length;
  const passedRuns = allRuns.filter(
    (r) => (r.metrics?.accuracy ?? 0) >= 0.85 && (r.guardrail_summary?.critical_violations ?? 0) === 0
  ).length;
  const failedRuns = totalRuns - passedRuns;

  const validAccuracyRuns = allRuns.filter((r) => typeof r.metrics?.accuracy === "number");
  const avgAccuracy =
    validAccuracyRuns.length > 0
      ? validAccuracyRuns.reduce((acc, r) => acc + (r.metrics.accuracy || 0), 0) / validAccuracyRuns.length
      : 0;

  const totalViolations = allRuns.reduce(
    (acc, r) => acc + (r.guardrail_summary?.total_violations || 0),
    0
  );

  // Prepare chart data chronologically
  const chronologicalRuns = [...allRuns].reverse();
  const qualityTrendData: DataPoint[] = chronologicalRuns.map((r, idx) => ({
    label: r.name ? r.name.substring(0, 10) : `Run #${idx + 1}`,
    value: r.metrics?.accuracy ?? 0,
    date: new Date(r.created_at).toLocaleDateString(),
  }));

  const faithfulnessData: DataPoint[] = chronologicalRuns.map((r, idx) => ({
    label: r.name ? r.name.substring(0, 10) : `Run #${idx + 1}`,
    value: r.metrics?.faithfulness ?? 0,
    date: new Date(r.created_at).toLocaleDateString(),
  }));

  const retrievalData: DataPoint[] = chronologicalRuns.map((r, idx) => ({
    label: r.name ? r.name.substring(0, 10) : `Run #${idx + 1}`,
    value: r.metrics?.retrieval_recall ?? 0,
    date: new Date(r.created_at).toLocaleDateString(),
  }));

  const safetyData: DataPoint[] = chronologicalRuns.map((r, idx) => ({
    label: r.name ? r.name.substring(0, 10) : `Run #${idx + 1}`,
    value: r.metrics?.safety ?? 0,
    date: new Date(r.created_at).toLocaleDateString(),
  }));

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Engineering Dashboard</h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time RAG evaluation runs, guardrails telemetry, and release gating status.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/projects"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/25 transition-colors cursor-pointer"
          >
            <Plus className="h-4 w-4" />
            Manage Projects
          </Link>
        </div>
      </div>

      {/* Summary Telemetry Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Projects</span>
            <FolderKanban className="h-4 w-4 text-indigo-400" />
          </div>
          <span className="text-2xl font-bold font-mono text-white">{totalProjects}</span>
        </div>

        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Evaluation Runs</span>
            <Activity className="h-4 w-4 text-indigo-400" />
          </div>
          <span className="text-2xl font-bold font-mono text-white">{totalRuns}</span>
        </div>

        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Passed Runs</span>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          </div>
          <span className="text-2xl font-bold font-mono text-emerald-400">{passedRuns}</span>
        </div>

        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Blocked / Failed</span>
            <XCircle className="h-4 w-4 text-rose-400" />
          </div>
          <span className="text-2xl font-bold font-mono text-rose-400">{failedRuns}</span>
        </div>

        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Avg Quality</span>
            <TrendingUp className="h-4 w-4 text-indigo-400" />
          </div>
          <span className="text-2xl font-bold font-mono text-indigo-300">
            {(avgAccuracy * 100).toFixed(1)}%
          </span>
        </div>

        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Violations</span>
            <ShieldAlert className="h-4 w-4 text-amber-400" />
          </div>
          <span className="text-2xl font-bold font-mono text-amber-400">{totalViolations}</span>
        </div>
      </div>

      {/* Real Charts Grid */}
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-4">
          Telemetry & Quality Trends (Real Evaluation History)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricTrendChart
            title="Accuracy / Correctness"
            metricName="Accuracy"
            data={qualityTrendData}
            color="#6366f1"
          />
          <MetricTrendChart
            title="Faithfulness / Grounding"
            metricName="Faithfulness"
            data={faithfulnessData}
            color="#10b981"
          />
          <MetricTrendChart
            title="Retrieval Recall"
            metricName="Recall"
            data={retrievalData}
            color="#06b6d4"
          />
          <MetricTrendChart
            title="Safety & Guardrails"
            metricName="Safety"
            data={safetyData}
            color="#8b5cf6"
          />
        </div>
      </div>

      {/* Recent Evaluations Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
        <div className="p-5 border-b border-slate-800/80 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white">Recent Evaluation Runs</h3>
            <p className="text-xs text-slate-400">Latest regression test cycles across your projects</p>
          </div>
        </div>

        {allRuns.length === 0 ? (
          <EmptyState
            title="No evaluations recorded yet"
            description="Run an evaluation on one of your datasets to track regressions and guardrail safety."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Run Name</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Accuracy</th>
                  <th className="py-3 px-4">Faithfulness</th>
                  <th className="py-3 px-4">Retrieval</th>
                  <th className="py-3 px-4">Violations</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {allRuns.slice(0, 8).map((run) => (
                  <tr key={run.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 px-4 font-sans font-medium text-slate-200">{run.name}</td>
                    <td className="py-3 px-4">
                      <StatusBadge status={run.status} />
                    </td>
                    <td className="py-3 px-4 text-slate-200">
                      {typeof run.metrics?.accuracy === "number"
                        ? `${(run.metrics.accuracy * 100).toFixed(1)}%`
                        : "—"}
                    </td>
                    <td className="py-3 px-4 text-slate-200">
                      {typeof run.metrics?.faithfulness === "number"
                        ? `${(run.metrics.faithfulness * 100).toFixed(1)}%`
                        : "—"}
                    </td>
                    <td className="py-3 px-4 text-slate-200">
                      {typeof run.metrics?.retrieval_recall === "number"
                        ? `${(run.metrics.retrieval_recall * 100).toFixed(1)}%`
                        : "—"}
                    </td>
                    <td className="py-3 px-4">
                      {(run.guardrail_summary?.total_violations ?? 0) > 0 ? (
                        <span className="text-rose-400 font-bold">
                          {run.guardrail_summary?.total_violations}
                        </span>
                      ) : (
                        <span className="text-emerald-400">0</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-sans">
                      {new Date(run.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 text-right font-sans">
                      <Link
                        to={`/projects/${run.project_id}/evaluations/${run.id}`}
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
