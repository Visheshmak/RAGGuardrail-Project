import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";
import { ProjectThresholdConfigItem } from "@/types";
import { ProjectTabs } from "@/components/ui/ProjectTabs";
import { LoadingState, ErrorState } from "@/components/ui/States";
import {
  Sliders,
  Cpu,
  ShieldCheck,
  Save,
  CheckCircle2,
  AlertCircle,
  Database,
  Layers,
  Sparkles,
} from "lucide-react";

export function ProjectSettingsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const queryClient = useQueryClient();
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Model & Pipeline Settings
  const [model, setModel] = useState("gpt-4o-mini");
  const [temperature, setTemperature] = useState(0.2);
  const [systemPrompt, setSystemPrompt] = useState(
    "You are a helpful and precise organizational AI assistant. Answer the question accurately using only the provided context snippets."
  );
  const [topK, setTopK] = useState(5);
  const [chunkSize, setChunkSize] = useState(500);
  const [chunkOverlap, setChunkOverlap] = useState(50);

  // Thresholds State
  const [thresholds, setThresholds] = useState({
    accuracy: { minimum: 0.9, max_regression: 0.03 },
    faithfulness: { minimum: 0.9, max_regression: 0.03 },
    retrieval_recall: { minimum: 0.85, max_regression: 0.05 },
    safety: { minimum: 0.98, max_regression: 0.01 },
  });
  const [blockOnCriticalGuardrail, setBlockOnCriticalGuardrail] = useState(true);

  // 1. Fetch threshold configuration
  const {
    data: thresholdConfig,
    isLoading: thresholdsLoading,
    isError: thresholdsError,
  } = useQuery<ProjectThresholdConfigItem>({
    queryKey: ["project-thresholds", projectId],
    queryFn: async () => {
      const res = await api.get(`/api/v1/projects/${projectId}/thresholds`);
      return res.data;
    },
    enabled: !!projectId,
  });

  useEffect(() => {
    if (thresholdConfig?.settings) {
      setModel(thresholdConfig.settings.model ?? "gpt-4o-mini");
      setTemperature(thresholdConfig.settings.temperature ?? 0.2);
      setSystemPrompt(thresholdConfig.settings.system_prompt ?? systemPrompt);
      setTopK(thresholdConfig.settings.top_k ?? 5);
      setChunkSize(thresholdConfig.settings.chunk_size ?? 500);
      setChunkOverlap(thresholdConfig.settings.chunk_overlap ?? 50);
    }
  }, [thresholdConfig]);

  useEffect(() => {
    if (thresholdConfig?.thresholds) {
      setThresholds((prev) => ({
        ...prev,
        ...thresholdConfig.thresholds,
      }));
      setBlockOnCriticalGuardrail(thresholdConfig.block_on_critical_guardrail ?? true);
    }
  }, [thresholdConfig]);

  // 2. Save thresholds mutation
  const saveMutation = useMutation({
    mutationFn: async () => {
      const res = await api.put(`/api/v1/projects/${projectId}/thresholds`, {
        thresholds,
        block_on_critical_guardrail: blockOnCriticalGuardrail,
        settings: { model, temperature, system_prompt: systemPrompt, top_k: topK, chunk_size: chunkSize, chunk_overlap: chunkOverlap },
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-thresholds", projectId] });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    },
  });

  if (thresholdsLoading) {
    return <LoadingState message="Loading project configuration and regression thresholds..." />;
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Project Configuration & Thresholds</h1>
          <p className="text-xs text-slate-400 mt-1">
            Tune LLM model parameters, vector retrieval chunking, and release gating regression thresholds.
          </p>
        </div>

        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md shadow-indigo-600/25 transition-colors cursor-pointer"
        >
          <Save className="h-4 w-4" />
          {saveMutation.isPending ? "Saving..." : "Save Settings"}
        </button>
      </div>

      {/* Navigation Sub-Tabs */}
      <ProjectTabs projectId={projectId!} />

      {saveSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-800/40 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
          <span>Configuration and release gating thresholds saved successfully.</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: LLM & Retrieval Hyperparameters */}
        <div className="space-y-6">
          {/* LLM Model Parameters */}
          <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-300">
              <Cpu className="h-4 w-4 text-indigo-400" />
              <span>LLM & Generation Parameters</span>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Model Engine</label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 font-mono"
                >
                  <option value="gpt-4o-mini">gpt-4o-mini (Default Fast & Accurate)</option>
                  <option value="gpt-4o">gpt-4o (High Reasoning)</option>
                  <option value="claude-3-5-sonnet">claude-3-5-sonnet</option>
                  <option value="meta-llama-3.1-70b">meta-llama-3.1-70b-instruct</option>
                </select>
              </div>

              <div>
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span>Temperature:</span>
                  <span className="font-mono text-slate-200">{temperature}</span>
                </div>
                <input
                  type="range"
                  min={0.0}
                  max={1.0}
                  step={0.05}
                  value={temperature}
                  onChange={(e) => setTemperature(Number(e.target.value))}
                  className="w-full accent-indigo-500 cursor-pointer"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">System Directive Prompt</label>
                <textarea
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  rows={3}
                  className="w-full p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none leading-relaxed"
                />
              </div>
            </div>
          </div>

          {/* Retrieval & Embedding Parameters */}
          <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-300">
              <Database className="h-4 w-4 text-indigo-400" />
              <span>Retrieval & Chunking Parameters</span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Top K Contexts</label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Default Chunk Size</label>
                <input
                  type="number"
                  min={100}
                  max={2000}
                  value={chunkSize}
                  onChange={(e) => setChunkSize(Number(e.target.value))}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 font-mono"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Regression Gating Thresholds */}
        <div className="space-y-6">
          <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm space-y-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-300">
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
              <span>Release Gating Thresholds</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              If an evaluation run drops below the minimum required score or regresses by more than the allowed delta, deployment will be automatically <strong>BLOCKED</strong>.
            </p>

            {/* Threshold Fields */}
            <div className="space-y-3.5">
              {/* Accuracy Threshold */}
              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <span className="text-xs font-bold text-slate-200 block">Accuracy / Match Threshold</span>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="block text-slate-400 mb-1 text-[11px]">Minimum Required</label>
                    <input
                      type="number"
                      step={0.01}
                      min={0.0}
                      max={1.0}
                      value={thresholds.accuracy?.minimum ?? 0.9}
                      onChange={(e) =>
                        setThresholds((prev) => ({
                          ...prev,
                          accuracy: { ...prev.accuracy, minimum: Number(e.target.value) },
                        }))
                      }
                      className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-100 font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 mb-1 text-[11px]">Max Allowed Regression</label>
                    <input
                      type="number"
                      step={0.01}
                      min={0.0}
                      max={0.5}
                      value={thresholds.accuracy?.max_regression ?? 0.03}
                      onChange={(e) =>
                        setThresholds((prev) => ({
                          ...prev,
                          accuracy: { ...prev.accuracy, max_regression: Number(e.target.value) },
                        }))
                      }
                      className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-100 font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Faithfulness Threshold */}
              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <span className="text-xs font-bold text-slate-200 block">Faithfulness / Grounding Threshold</span>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="block text-slate-400 mb-1 text-[11px]">Minimum Required</label>
                    <input
                      type="number"
                      step={0.01}
                      min={0.0}
                      max={1.0}
                      value={thresholds.faithfulness?.minimum ?? 0.9}
                      onChange={(e) =>
                        setThresholds((prev) => ({
                          ...prev,
                          faithfulness: { ...prev.faithfulness, minimum: Number(e.target.value) },
                        }))
                      }
                      className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-100 font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 mb-1 text-[11px]">Max Allowed Regression</label>
                    <input
                      type="number"
                      step={0.01}
                      min={0.0}
                      max={0.5}
                      value={thresholds.faithfulness?.max_regression ?? 0.03}
                      onChange={(e) =>
                        setThresholds((prev) => ({
                          ...prev,
                          faithfulness: { ...prev.faithfulness, max_regression: Number(e.target.value) },
                        }))
                      }
                      className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-100 font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Retrieval Recall Threshold */}
              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <span className="text-xs font-bold text-slate-200 block">Retrieval Recall Threshold</span>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="block text-slate-400 mb-1 text-[11px]">Minimum Required</label>
                    <input
                      type="number"
                      step={0.01}
                      min={0.0}
                      max={1.0}
                      value={thresholds.retrieval_recall?.minimum ?? 0.85}
                      onChange={(e) =>
                        setThresholds((prev) => ({
                          ...prev,
                          retrieval_recall: { ...prev.retrieval_recall, minimum: Number(e.target.value) },
                        }))
                      }
                      className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-100 font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 mb-1 text-[11px]">Max Allowed Regression</label>
                    <input
                      type="number"
                      step={0.01}
                      min={0.0}
                      max={0.5}
                      value={thresholds.retrieval_recall?.max_regression ?? 0.05}
                      onChange={(e) =>
                        setThresholds((prev) => ({
                          ...prev,
                          retrieval_recall: { ...prev.retrieval_recall, max_regression: Number(e.target.value) },
                        }))
                      }
                      className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-100 font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Safety Threshold */}
              <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <span className="text-xs font-bold text-slate-200 block">Safety & Content Integrity Threshold</span>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="block text-slate-400 mb-1 text-[11px]">Minimum Required</label>
                    <input
                      type="number"
                      step={0.01}
                      min={0.0}
                      max={1.0}
                      value={thresholds.safety?.minimum ?? 0.98}
                      onChange={(e) =>
                        setThresholds((prev) => ({
                          ...prev,
                          safety: { ...prev.safety, minimum: Number(e.target.value) },
                        }))
                      }
                      className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-100 font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 mb-1 text-[11px]">Max Allowed Regression</label>
                    <input
                      type="number"
                      step={0.01}
                      min={0.0}
                      max={0.5}
                      value={thresholds.safety?.max_regression ?? 0.01}
                      onChange={(e) =>
                        setThresholds((prev) => ({
                          ...prev,
                          safety: { ...prev.safety, max_regression: Number(e.target.value) },
                        }))
                      }
                      className="w-full px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-100 font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Critical Guardrail Violation Gate */}
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-xs">
                <div>
                  <span className="font-semibold text-slate-200 block">Strict Guardrail Gating</span>
                  <span className="text-[11px] text-slate-400">Block release immediately on any critical safety violation</span>
                </div>
                <input
                  type="checkbox"
                  checked={blockOnCriticalGuardrail}
                  onChange={(e) => setBlockOnCriticalGuardrail(e.target.checked)}
                  className="h-4 w-4 rounded accent-indigo-600 bg-slate-900 border-slate-700 cursor-pointer"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
