export interface User {
  id: string;
  email: string;
  name: string;
  role: "admin" | "member" | "viewer";
  created_at: string;
}

export interface Project {
  id: string;
  name: string;
  description?: string | null;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentItem {
  id: string;
  project_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED";
  chunk_count: number;
  error_message?: string | null;
  chunking_config: {
    chunk_size: number;
    chunk_overlap: number;
  };
  created_at: string;
  updated_at: string;
}

export interface DocumentChunkItem {
  id: string;
  document_id: string;
  project_id: string;
  chunk_index: number;
  content: string;
  page_number?: number | null;
  metadata: Record<string, any>;
  created_at: string;
}

export interface DatasetItem {
  id: string;
  project_id: string;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
  versions?: DatasetVersionItem[];
}

export interface DatasetVersionItem {
  id: string;
  dataset_id: string;
  version: number;
  case_count: number;
  description?: string | null;
  created_at: string;
}

export interface EvaluationCaseItem {
  id: string;
  dataset_version_id: string;
  question: string;
  expected_answer?: string | null;
  expected_context?: string[];
  category: string;
  difficulty: string;
  case_metadata?: Record<string, any>;
  created_at: string;
}

export interface GuardrailResultItem {
  guardrail: string;
  passed: boolean;
  severity: "low" | "medium" | "high" | "critical";
  reason: string;
  metadata?: Record<string, any>;
}

export interface GuardrailConfigItem {
  id: string;
  project_id: string;
  guardrail_type: string;
  name: string;
  description?: string | null;
  is_enabled: boolean;
  target: "input" | "output" | "both";
  severity_override?: string | null;
  action_override?: string | null;
  parameters: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface GuardrailExecutionLogItem {
  id: string;
  project_id: string;
  evaluation_case_id?: string | null;
  guardrail_name: string;
  target: string;
  passed: boolean;
  severity: string;
  action_taken: "allow" | "log" | "warning" | "block";
  reason: string;
  execution_metadata: Record<string, any>;
  latency_ms: number;
  created_at: string;
}

export interface EvaluationRunItem {
  id: string;
  project_id: string;
  dataset_version_id?: string | null;
  name: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  total_cases: number;
  completed_cases: number;
  metrics: {
    accuracy?: number;
    retrieval_recall?: number;
    faithfulness?: number;
    answer_relevance?: number;
    safety?: number;
    latency_ms?: number;
  };
  guardrail_summary: {
    total_violations?: number;
    critical_violations?: number;
    high_violations?: number;
  };
  configuration_snapshot: Record<string, any>;
  created_at: string;
  completed_at?: string | null;
}

export interface EvaluationCaseResultItem {
  id: string;
  evaluation_run_id: string;
  evaluation_case_id?: string | null;
  question: string;
  expected_answer?: string | null;
  actual_answer?: string | null;
  retrieved_chunks: Array<{
    document?: string;
    text?: string;
    score?: number;
    page?: number | null;
  }>;
  metrics: {
    accuracy?: number;
    retrieval_recall?: number;
    faithfulness?: number;
    answer_relevance?: number;
  };
  guardrail_results: GuardrailResultItem[];
  passed: boolean;
  latency_ms: number;
  created_at: string;
}

export interface BaselineItem {
  id: string;
  project_id: string;
  evaluation_run_id: string;
  version: number;
  is_active: boolean;
  configuration_snapshot: Record<string, any>;
  metrics_snapshot: Record<string, number>;
  notes?: string | null;
  created_at: string;
}

export interface MetricRegressionDetailItem {
  metric: string;
  baseline: number;
  current: number;
  allowed_regression: number;
  actual_regression: number;
  status: "PASS" | "WARNING" | "FAIL";
  reason?: string | null;
}

export interface ReleaseDecisionItem {
  decision: "PASS" | "WARNING" | "BLOCK";
  passed: boolean;
  reasons: Array<{
    metric?: string;
    baseline?: number;
    current?: number;
    minimum_required?: number;
    allowed_regression?: number;
    actual_regression?: number;
    reason?: string;
    critical_violations?: number;
  }>;
  metrics_comparison?: MetricRegressionDetailItem[];
  baseline_version?: number | null;
  evaluation_run_id?: string | null;
}

export interface ProjectThresholdConfigItem {
  id: string;
  project_id: string;
  thresholds: Record<string, { minimum: number; max_regression: number }>;
  block_on_critical_guardrail: boolean;
  settings: {
    model?: string;
    temperature?: number;
    system_prompt?: string;
    top_k?: number;
    chunk_size?: number;
    chunk_overlap?: number;
  };
  created_at: string;
  updated_at: string;
}

export interface SourceCitationItem {
  document: string;
  document_id: string;
  chunk_id: string;
  page?: number | null;
  chunk_index: number;
  text: string;
  score: number;
}

export interface QueryResponseItem {
  question: string;
  answer: string;
  sources: SourceCitationItem[];
  model: string;
  latency_ms: number;
  blocked: boolean;
  action: string;
  guardrail_results: GuardrailResultItem[];
}
