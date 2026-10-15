import React, { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";
import { DocumentItem, DocumentChunkItem } from "@/types";
import { ProjectTabs } from "@/components/ui/ProjectTabs";
import { StatusBadge } from "@/components/ui/Badge";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/States";
import {
  FileText,
  Upload,
  Trash2,
  Layers,
  CheckCircle2,
  AlertCircle,
  Eye,
  X,
  FileCode,
} from "lucide-react";
import { clsx } from "clsx";

export function DocumentsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const queryClient = useQueryClient();
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [chunkSize, setChunkSize] = useState(500);
  const [chunkOverlap, setChunkOverlap] = useState(50);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);

  // 1. Fetch documents with polling for queued/processing documents
  const {
    data: documents = [],
    isLoading: docsLoading,
    isError: docsError,
    refetch,
  } = useQuery<DocumentItem[]>({
    queryKey: ["project-documents", projectId],
    queryFn: async () => {
      const res = await api.get(`/api/v1/projects/${projectId}/documents`);
      return res.data;
    },
    enabled: !!projectId,
    refetchInterval: (query) => {
      const hasActive = query.state.data?.some(
        (d) => d.status === "QUEUED" || d.status === "PROCESSING"
      );
      return hasActive ? 2000 : false;
    },
  });

  // 2. Fetch chunks for selected document
  const { data: chunks = [], isLoading: chunksLoading } = useQuery<DocumentChunkItem[]>({
    queryKey: ["document-chunks", projectId, selectedDocId],
    queryFn: async () => {
      if (!selectedDocId) return [];
      const res = await api.get(`/api/v1/projects/${projectId}/documents/${selectedDocId}/chunks`);
      return res.data;
    },
    enabled: !!selectedDocId,
  });

  // 3. Upload document mutation
  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Please select a file to upload");
      setUploadError(null);

      const formData = new FormData();
      formData.append("file", file);
      formData.append("chunk_size", chunkSize.toString());
      formData.append("chunk_overlap", chunkOverlap.toString());

      const res = await api.post(`/api/v1/projects/${projectId}/documents/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-documents", projectId] });
      setShowUploadModal(false);
      setFile(null);
    },
    onError: (err: any) => {
      setUploadError(err.response?.data?.detail || err.message || "Failed to upload document.");
    },
  });

  // 4. Delete document mutation
  const deleteMutation = useMutation({
    mutationFn: async (docId: string) => {
      await api.delete(`/api/v1/projects/${projectId}/documents/${docId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project-documents", projectId] });
      if (selectedDocId) setSelectedDocId(null);
    },
  });

  if (docsLoading) {
    return <LoadingState message="Loading documents and vector store status..." />;
  }

  if (docsError) {
    return <ErrorState message="Could not fetch project documents." onRetry={refetch} />;
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Document Ingestion & Chunks</h1>
          <p className="text-xs text-slate-400 mt-1">
            Knowledge base documents indexed into Qdrant vector database for RAG retrieval.
          </p>
        </div>

        <button
          onClick={() => setShowUploadModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-md shadow-indigo-600/25 transition-colors cursor-pointer"
        >
          <Upload className="h-4 w-4" />
          Upload Document
        </button>
      </div>

      {/* Navigation Sub-Tabs */}
      <ProjectTabs projectId={projectId!} />

      {/* Documents List */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
        {documents.length === 0 ? (
          <EmptyState
            title="No knowledge documents uploaded yet"
            description="Upload PDF, DOCX, Markdown, or TXT documents to start querying your RAG knowledge base."
            action={
              <button
                onClick={() => setShowUploadModal(true)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors cursor-pointer"
              >
                <Upload className="h-4 w-4" />
                Upload Document
              </button>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Filename</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Size</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Indexed Chunks</th>
                  <th className="py-3 px-4">Uploaded At</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {documents.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="py-3.5 px-4 font-sans font-medium text-slate-200 flex items-center gap-2">
                      <FileText className="h-4 w-4 text-indigo-400 shrink-0" />
                      <span className="truncate max-w-xs">{d.filename}</span>
                    </td>
                    <td className="py-3.5 px-4 uppercase text-slate-400">{d.file_type}</td>
                    <td className="py-3.5 px-4 text-slate-400">
                      {(d.file_size / 1024).toFixed(1)} KB
                    </td>
                    <td className="py-3.5 px-4 font-sans">
                      <StatusBadge status={d.status} />
                    </td>
                    <td className="py-3.5 px-4 text-slate-200 font-bold">{d.chunk_count}</td>
                    <td className="py-3.5 px-4 text-slate-400 font-sans">
                      {new Date(d.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 px-4 text-right font-sans flex items-center justify-end gap-2">
                      <button
                        onClick={() => setSelectedDocId(d.id)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-400 hover:bg-slate-800 transition-colors cursor-pointer"
                        title="View extracted chunks"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm(`Delete "${d.filename}" and remove its vector embeddings?`)) {
                            deleteMutation.mutate(d.id);
                          }
                        }}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors cursor-pointer"
                        title="Delete document"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Upload Document Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                  <Upload className="h-4 w-4" />
                </div>
                <h3 className="text-sm font-semibold text-white">Upload Knowledge Document</h3>
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

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Select Document</label>
                <input
                  type="file"
                  accept=".pdf,.docx,.txt,.md"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer"
                />
                <p className="text-[11px] text-slate-500 mt-1">Supported formats: PDF, DOCX, TXT, Markdown (Max 25MB)</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Chunk Size (chars)</label>
                  <input
                    type="number"
                    value={chunkSize}
                    onChange={(e) => setChunkSize(Number(e.target.value))}
                    min={100}
                    max={2000}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Chunk Overlap</label>
                  <input
                    type="number"
                    value={chunkOverlap}
                    onChange={(e) => setChunkOverlap(Number(e.target.value))}
                    min={0}
                    max={500}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 font-mono"
                  />
                </div>
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
                {uploadMutation.isPending ? "Indexing..." : "Upload & Ingest"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Chunk Viewer Modal */}
      {selectedDocId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-3xl max-h-[85vh] bg-slate-900 border border-slate-800 rounded-2xl flex flex-col overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800/80 bg-slate-900/50">
              <div className="flex items-center gap-2">
                <FileCode className="h-4 w-4 text-indigo-400" />
                <h3 className="text-sm font-semibold text-white">Extracted Document Chunks ({chunks.length})</h3>
              </div>
              <button onClick={() => setSelectedDocId(null)} className="text-slate-400 hover:text-slate-200">
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-3">
              {chunksLoading ? (
                <LoadingState message="Fetching chunk vectors..." />
              ) : chunks.length === 0 ? (
                <p className="text-xs text-slate-400 text-center py-6">No chunks generated yet.</p>
              ) : (
                chunks.map((c) => (
                  <div key={c.id} className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-xs space-y-1.5">
                    <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 pb-1 border-b border-slate-800/60">
                      <span>Chunk #{c.chunk_index + 1}</span>
                      {c.page_number && <span>Page: {c.page_number}</span>}
                    </div>
                    <p className="text-slate-200 leading-relaxed font-sans">{c.content}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
