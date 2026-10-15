import React, { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";
import { DatasetItem, EvaluationCaseItem } from "@/types";
import { ProjectTabs } from "@/components/ui/ProjectTabs";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/States";
import {
  Database,
  Plus,
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  Layers,
  Sparkles,
  X,
} from "lucide-react";
import { clsx } from "clsx";

export function DatasetsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const queryClient = useQueryClient();
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [datasetName, setDatasetName] = useState("");
  const [datasetDescription, setDatasetDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // 1. Fetch datasets
  const {
    data: datasets = [],
    isLoading: datasetsLoading,
    isError: datasetsError,
    refetch,
  } = useQuery<DatasetItem[]>({
    queryKey: ["project-datasets", projectId],
    queryFn: async () => {
      const res = await api.get(`/api/v1/projects/${projectId}/datasets`);
      return res.data;
    },
    enabled: !!projectId,
  });

  // Automatically select first version
  const activeVersionId =
    selectedVersionId ||
    datasets.find((d) => d.versions && d.versions.length > 0)?.versions?.[0]?.id ||
    null;
  const activeDataset = datasets.find((dataset) =>
    dataset.versions?.some((version) => version.id === activeVersionId)
  );

  // 2. Fetch test cases for selected version
  const { data: testCases = [], isLoading: casesLoading } = useQuery<EvaluationCaseItem[]>({
    queryKey: ["dataset-cases", activeDataset?.id, activeVersionId],
    queryFn: async () => {
      if (!activeVersionId || !activeDataset) return [];
      const res = await api.get(
        `/api/v1/datasets/${activeDataset.id}/versions/${activeVersionId}/cases`
      );
      return res.data;
    },
    enabled: !!activeVersionId && !!activeDataset,
  });

  // 3. Upload dataset mutation
  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Please select a file to upload");
      setUploadError(null);

      const datasetResponse = await api.post(`/api/v1/projects/${projectId}/datasets`, {
        name: datasetName || file.name.replace(/\.[^/.]+$/, ""),
        description: datasetDescription || undefined,
      });
      const formData = new FormData();
      formData.append("file", file);
      if (datasetDescription) formData.append("description", datasetDescription);

      const res = await api.post(`/api/v1/datasets/${datasetResponse.data.id}/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return { ...res.data, dataset_id: datasetResponse.data.id };
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["project-datasets", projectId] });
      setShowUploadModal(false);
      setFile(null);
      setDatasetName("");
      setDatasetDescription("");
      if (data.version_id) {
        setSelectedVersionId(data.version_id);
      }
    },
    onError: (err: any) => {
      setUploadError(err.response?.data?.detail || err.message || "Failed to upload dataset.");
    },
  });

  if (datasetsLoading) {
    return <LoadingState message="Loading datasets and test cases..." />;
  }

  if (datasetsError) {
    return <ErrorState message="Could not load project datasets." onRetry={refetch} />;
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Datasets & Test Cases</h1>
          <p className="text-xs text-slate-400 mt-1">
            Golden benchmark test cases, versioned Q&A pairs, and expected context for RAG evaluation.
          </p>
        </div>

        <button
          onClick={() => setShowUploadModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/25 transition-colors cursor-pointer"
        >
          <Upload className="h-4 w-4" />
          Upload Dataset (CSV / JSON)
        </button>
      </div>

      {/* Navigation Sub-Tabs */}
      <ProjectTabs projectId={projectId!} />

      {datasets.length === 0 ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-8">
          <EmptyState
            title="No evaluation datasets available"
            description="Upload golden Q&A pairs (CSV or JSON) to benchmark accuracy, recall, and safety."
            action={
              <button
                onClick={() => setShowUploadModal(true)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors cursor-pointer"
              >
                <Upload className="h-4 w-4" />
                Upload Dataset
              </button>
            }
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Datasets & Versions Sidebar */}
          <div className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Dataset Versions
            </h3>
            <div className="space-y-2">
              {datasets.map((d) => (
                <div key={d.id} className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-200 truncate">{d.name}</span>
                    <span className="text-[10px] text-slate-400 font-mono">
                      {d.versions?.length || 0} ver
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-1">{d.description || "Golden evaluation dataset"}</p>

                  <div className="pt-2 border-t border-slate-800/60 space-y-1">
                    {d.versions?.map((v) => (
                      <button
                        key={v.id}
                        onClick={() => setSelectedVersionId(v.id)}
                        className={clsx(
                          "w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-mono transition-colors text-left cursor-pointer",
                          activeVersionId === v.id
                            ? "bg-indigo-600/15 text-indigo-400 font-semibold border border-indigo-500/20"
                            : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"
                        )}
                      >
                        <span>Version {v.version}</span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-300">
                          {v.case_count} cases
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Test Cases Table */}
          <div className="lg:col-span-3 rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
            <div className="p-4 border-b border-slate-800/80 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-white">Benchmark Test Cases Preview</h3>
                <p className="text-xs text-slate-400">
                  Showing {testCases.length} golden test questions for current dataset version
                </p>
              </div>
            </div>

            {casesLoading ? (
              <LoadingState message="Loading test cases..." />
            ) : testCases.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400">No test cases in this version.</div>
            ) : (
              <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/80 text-slate-400 font-semibold uppercase tracking-wider sticky top-0 border-b border-slate-800">
                    <tr>
                      <th className="py-3 px-4 w-12">#</th>
                      <th className="py-3 px-4">Question</th>
                      <th className="py-3 px-4">Expected Ground Truth Answer</th>
                      <th className="py-3 px-4">Category</th>
                      <th className="py-3 px-4">Difficulty</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {testCases.map((c, idx) => (
                      <tr key={c.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 px-4 font-mono text-slate-500">{idx + 1}</td>
                        <td className="py-3 px-4 font-medium text-slate-200 max-w-xs leading-relaxed">
                          {c.question}
                        </td>
                        <td className="py-3 px-4 text-slate-300 max-w-sm leading-relaxed">
                          {c.expected_answer || <span className="text-slate-500 italic">Open-ended</span>}
                        </td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] font-mono capitalize">
                            {c.category || "general"}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={clsx(
                              "px-2 py-0.5 rounded text-[10px] font-mono capitalize",
                              c.difficulty === "hard"
                                ? "bg-rose-950/40 text-rose-400"
                                : c.difficulty === "easy"
                                ? "bg-emerald-950/40 text-emerald-400"
                                : "bg-amber-950/40 text-amber-400"
                            )}
                          >
                            {c.difficulty || "medium"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Upload Dataset Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                  <Upload className="h-4 w-4" />
                </div>
                <h3 className="text-sm font-semibold text-white">Upload Dataset</h3>
              </div>
              <button
                onClick={() => setShowUploadModal(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {uploadError && (
              <div className="p-3 rounded-xl bg-rose-950/20 border border-rose-800/40 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{uploadError}</span>
              </div>
            )}

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Dataset Name</label>
                <input
                  type="text"
                  value={datasetName}
                  onChange={(e) => setDatasetName(e.target.value)}
                  placeholder="e.g. Enterprise Policy Gold Standard"
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Description (Optional)</label>
                <input
                  type="text"
                  value={datasetDescription}
                  onChange={(e) => setDatasetDescription(e.target.value)}
                  placeholder="e.g. 50 test questions covering leave, security, and benefits"
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Select File (CSV or JSON)</label>
                <input
                  type="file"
                  accept=".csv,.json"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer"
                />
                <p className="text-[11px] text-slate-500 mt-1.5">
                  CSV must contain: <code>question</code> and optionally <code>expected_answer</code>.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                type="button"
                onClick={() => setShowUploadModal(false)}
                className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-slate-200 rounded-lg transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => uploadMutation.mutate()}
                disabled={!file || uploadMutation.isPending}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow-md shadow-indigo-600/25 transition-colors cursor-pointer"
              >
                {uploadMutation.isPending ? "Uploading..." : "Upload & Parse"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
