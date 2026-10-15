import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";
import { EvaluationRunItem, DatasetItem } from "@/types";
import { ProjectTabs } from "@/components/ui/ProjectTabs";
import { StatusBadge } from "@/components/ui/Badge";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/States";
import {
  Activity,
  Plus,
  Play,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Clock,
  X,
} from "lucide-react";

export function EvaluationsListPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const queryClient = useQueryClient();
  const [showRunModal, setShowRunModal] = useState(false);
  const [runName, setRunName] = useState("");
  const [selectedDatasetVersionId, setSelectedDatasetVersionId] = useState("");

  // 1. Fetch project evaluation runs
  const {
    data: runs = [],
    isLoading: runsLoading,
    isError: runsError,
    refetch,
  } = useQuery<EvaluationRunItem[]>({
    queryKey: ["project-evaluations", projectId],
    queryFn: async () => {
      const res = await api.get(`/api/v1/projects/${projectId}/evaluations`);
      return res.data;
    },
    enabled: !!projectId,
    refetchInterval: (query) => {
      const hasActive = query.state.data?.some(
        (r) => r.status === "RUNNING" || r.status === "PENDING"
      );
      return hasActive ? 2000 : false;
    },
  });

  // 2. Fetch project datasets & versions
  const { data: datasets = [] } = useQuery<DatasetItem[]>({
    queryKey: ["project-datasets", projectId],
    queryFn: async () => {
      const res = await api.get(`/api/v1/projects/${projectId}/datasets`);
      return res.data;
    },
    enabled: !!projectId,
  });

  // 3. Trigger evaluation run mutation
  const runMutation = useMutation({
    mutationFn: async (payload: { name: string; dataset_version_id: string }) => {
      const res = await api.post(`/api/v1/projects/${projectId}/evaluations`, payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-evaluations", projectId] });
      setShowRunModal(false);
      setRunName("");
      setSelectedDatasetVersionId("");
    },
  });

  const handleCreateRun = (e: React.FormEvent) => {
    e.preventDefault();
    if (!runName.trim() || !selectedDatasetVersionId) return;

    runMutation.mutate({
      name: runName.trim(),
      dataset_version_id: selectedDatasetVersionId,
    });
  };

  if (runsLoading) {
    return <LoadingState message="Loading evaluation history..." />;
  }

  if (runsError) {
    return <ErrorState message="Could not fetch evaluation runs." onRetry={refetch} />;
  }

  // Extract all dataset versions
  const allVersions = datasets.flatMap((d) =>
    (d.versions || []).map((v) => ({
      ...v,
      datasetName: d.name,
    }))
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Evaluation Runs</h1>
          <p className="text-xs text-slate-400 mt-1">
            Execute test suites, inspect retrieval recall, and enforce release gating against active baselines.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setShowRunModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/25 transition-colors cursor-pointer"
          >
            <Plus className="h-4 w-4" />
            New Evaluation Run
          </button>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <ProjectTabs projectId={projectId!} />

      {/* Evaluations Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
        {runs.length === 0 ? (
          <EmptyState
            title="No evaluation runs yet"
            description="Launch an evaluation on your dataset to monitor quality and catch regressions."
            action={
              <button
                onClick={() => setShowRunModal(true)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors cursor-pointer"
              >
                <Plus className="h-4 w-4" />
                Launch Evaluation
              </button>
            }
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
                  <th className="py-3 px-4">Retrieval Recall</th>
                  <th className="py-3 px-4">Safety</th>
                  <th className="py-3 px-4">Violations</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {runs.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3.5 px-4 font-sans font-medium text-slate-200">
                      <Link
                        to={`/projects/${projectId}/evaluations/${r.id}`}
                        className="hover:text-indigo-400 transition-colors"
                      >
                        {r.name}
                      </Link>
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="py-3.5 px-4 text-slate-200">
                      {typeof r.metrics?.accuracy === "number"
                        ? `${(r.metrics.accuracy * 100).toFixed(1)}%`
                        : "—"}
                    </td>
                    <td className="py-3.5 px-4 text-slate-200">
                      {typeof r.metrics?.faithfulness === "number"
                        ? `${(r.metrics.faithfulness * 100).toFixed(1)}%`
                        : "—"}
                    </td>
                    <td className="py-3.5 px-4 text-slate-200">
                      {typeof r.metrics?.retrieval_recall === "number"
                        ? `${(r.metrics.retrieval_recall * 100).toFixed(1)}%`
                        : "—"}
                    </td>
                    <td className="py-3.5 px-4 text-slate-200">
                      {typeof r.metrics?.safety === "number"
                        ? `${(r.metrics.safety * 100).toFixed(1)}%`
                        : "—"}
                    </td>
                    <td className="py-3.5 px-4">
                      {(r.guardrail_summary?.total_violations ?? 0) > 0 ? (
                        <span className="text-rose-400 font-bold">
                          {r.guardrail_summary?.total_violations}
                        </span>
                      ) : (
                        <span className="text-emerald-400">0</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-slate-400 font-sans">
                      {new Date(r.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 px-4 text-right font-sans">
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

      {/* New Evaluation Run Modal */}
      {showRunModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                  <Activity className="h-4 w-4" />
                </div>
                <h3 className="text-sm font-semibold text-white">New Evaluation Run</h3>
              </div>
              <button
                onClick={() => setShowRunModal(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleCreateRun} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Run Name</label>
                <input
                  type="text"
                  required
                  value={runName}
                  onChange={(e) => setRunName(e.target.value)}
                  placeholder="e.g. Model v2 - 500 Token Chunking"
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Select Dataset Version
                </label>
                {allVersions.length > 0 ? (
                  <select
                    value={selectedDatasetVersionId}
                    onChange={(e) => setSelectedDatasetVersionId(e.target.value)}
                    required
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="">Select a dataset version...</option>
                    {allVersions.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.datasetName} (v{v.version} - {v.case_count} cases)
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800/80 text-[11px] text-slate-400">
                    No datasets uploaded yet. Upload a dataset under the Datasets tab before starting an evaluation.
                  </div>
                )}
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setShowRunModal(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 rounded-lg transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={runMutation.isPending || !selectedDatasetVersionId}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow-md shadow-indigo-600/25 transition-colors cursor-pointer"
                >
                  {runMutation.isPending ? "Executing..." : "Start Evaluation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
