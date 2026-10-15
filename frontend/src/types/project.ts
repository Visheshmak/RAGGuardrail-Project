export interface Project {
  id: string;
  name: string;
  description?: string | null;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
}
