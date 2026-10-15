import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { projectService } from "@/services/projectService";
import type { ProjectCreate } from "@/types/project";
import { 
  FolderPlus, 
  Search, 
  Trash2, 
  ExternalLink, 
  Calendar, 
  Layers, 
  X, 
  Loader2, 
  AlertCircle,
  FolderGit2
} from "lucide-react";

export function ProjectListPage() {
  const [search, setSearch] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newProject, setNewProject] = useState<ProjectCreate>({ name: "", description: "" });
  const [formError, setFormError] = useState<string | null>(null);

  const queryClient = useQueryClient();

  const { data: projects = [], isLoading, error } = useQuery({
    queryKey: ["projects"],
    queryFn: projectService.getProjects,
  });

  const createMutation = useMutation({
    mutationFn: (payload: ProjectCreate) => projectService.createProject(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setIsModalOpen(false);
      setNewProject({ name: "", description: "" });
      setFormError(null);
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.detail || "Failed to create project");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => projectService.deleteProject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProject.name.trim()) {
      setFormError("Project name is required.");
      return;
    }
    createMutation.mutate(newProject);
  };

  const filteredProjects = projects.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    (p.description && p.description.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Top action header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
            <FolderGit2 className="h-6 w-6 text-indigo-400" />
            Evaluation Projects
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Manage your RAG evaluation datasets, guardrail baselines, and test suites
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-medium text-sm shadow-lg shadow-indigo-600/25 transition-all cursor-pointer"
        >
          <FolderPlus className="h-4 w-4" />
          Create Project
        </button>
      </div>

      {/* Search & Stats Bar */}
      <div className="flex items-center justify-between gap-4 p-4 rounded-xl bg-slate-900/60 border border-slate-800/80">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search projects by name or description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-950/60 border border-slate-800 rounded-lg text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 transition-all"
          />
        </div>

        <div className="text-xs text-slate-400 font-medium">
          Showing <span className="text-indigo-400 font-semibold">{filteredProjects.length}</span> of {projects.length} projects
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/50 flex items-center gap-3 text-rose-300 text-sm">
          <AlertCircle className="h-5 w-5 shrink-0 text-rose-400" />
          <span>Failed to load projects. Please refresh or verify API connection.</span>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="py-20 flex flex-col items-center justify-center gap-3 text-slate-400">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
          <p className="text-sm">Fetching projects...</p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && filteredProjects.length === 0 && (
        <div className="py-16 text-center border border-dashed border-slate-800 rounded-2xl bg-slate-900/30">
          <Layers className="h-12 w-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-300">No projects found</h3>
          <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">
            {search
              ? "No projects matched your search query. Try adjusting your filter."
              : "Get started by creating your first RAG evaluation project."}
          </p>
          {!search && (
            <button
              onClick={() => setIsModalOpen(true)}
              className="mt-5 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors cursor-pointer"
            >
              <FolderPlus className="h-4 w-4" />
              New Project
            </button>
          )}
        </div>
      )}

      {/* Project Grid */}
      {!isLoading && filteredProjects.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredProjects.map((project) => (
            <div
              key={project.id}
              className="group flex flex-col justify-between p-5 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition-all shadow-lg shadow-black/20 hover:shadow-indigo-950/20"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <h3 className="font-semibold text-base text-slate-100 group-hover:text-indigo-300 transition-colors line-clamp-1">
                    {project.name}
                  </h3>
                  <button
                    onClick={() => {
                      if (confirm(`Are you sure you want to delete project "${project.name}"?`)) {
                        deleteMutation.mutate(project.id);
                      }
                    }}
                    title="Delete project"
                    className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-rose-400 p-1 rounded hover:bg-rose-950/30 transition-all cursor-pointer"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>

                <p className="text-xs text-slate-400 mt-2 line-clamp-2 min-h-[2rem]">
                  {project.description || "No description provided."}
                </p>
              </div>

              <div className="mt-5 pt-4 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500">
                <div className="flex items-center gap-1.5">
                  <Calendar className="h-3.5 w-3.5" />
                  <span>{new Date(project.created_at).toLocaleDateString()}</span>
                </div>
                <Link
                  to={`/projects/${project.id}`}
                  aria-label={`Open project ${project.name}`}
                  className="inline-flex items-center gap-1 px-2 py-1 -mr-2 rounded-md text-indigo-400 font-medium hover:text-indigo-300 hover:bg-indigo-500/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 transition-colors"
                >
                  <span>Open</span>
                  <ExternalLink className="h-3 w-3" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <FolderPlus className="h-5 w-5 text-indigo-400" />
                Create New Project
              </h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {formError && (
              <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-800/50 flex items-start gap-2.5 text-rose-300 text-xs">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Project Name *
                </label>
                <input
                  type="text"
                  required
                  value={newProject.name}
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  placeholder="e.g., Customer Support Bot Evaluation"
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-800 rounded-xl text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Description (Optional)
                </label>
                <textarea
                  rows={3}
                  value={newProject.description || ""}
                  onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                  placeholder="Summary of domain, datasets, or evaluation objectives..."
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-800 rounded-xl text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all resize-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 transition-colors cursor-pointer disabled:opacity-50"
                >
                  {createMutation.isPending ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    "Create Project"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
