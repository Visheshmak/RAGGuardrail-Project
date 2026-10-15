import { api } from "./api";
import type { Project, ProjectCreate, ProjectUpdate } from "@/types/project";

export const projectService = {
  async getProjects(): Promise<Project[]> {
    const response = await api.get<Project[]>("/api/v1/projects");
    return response.data;
  },

  async getProject(id: string): Promise<Project> {
    const response = await api.get<Project>(`/api/v1/projects/${id}`);
    return response.data;
  },

  async createProject(payload: ProjectCreate): Promise<Project> {
    const response = await api.post<Project>("/api/v1/projects", payload);
    return response.data;
  },

  async updateProject(id: string, payload: ProjectUpdate): Promise<Project> {
    const response = await api.put<Project>(`/api/v1/projects/${id}`, payload);
    return response.data;
  },

  async deleteProject(id: string): Promise<void> {
    await api.delete(`/api/v1/projects/${id}`);
  },
};
