import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/hooks/useAuth";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { DashboardLayout } from "@/layouts/DashboardLayout";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { DashboardOverviewPage } from "@/pages/DashboardOverviewPage";
import { ProjectListPage } from "@/pages/ProjectListPage";
import { ProjectOverviewPage } from "@/pages/ProjectOverviewPage";
import { EvaluationsListPage } from "@/pages/EvaluationsListPage";
import { EvaluationDetailPage } from "@/pages/EvaluationDetailPage";
import { DatasetsPage } from "@/pages/DatasetsPage";
import { GuardrailsPage } from "@/pages/GuardrailsPage";
import { DocumentsPage } from "@/pages/DocumentsPage";
import { PlaygroundPage } from "@/pages/PlaygroundPage";
import { ProjectSettingsPage } from "@/pages/ProjectSettingsPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <AuthProvider>
          <Routes>
            {/* Public authentication routes */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Protected enterprise dashboard routes */}
            <Route element={<ProtectedRoute />}>
              <Route element={<DashboardLayout />}>
                {/* Global Dashboard Overview */}
                <Route path="/" element={<DashboardOverviewPage />} />

                {/* Projects Management */}
                <Route path="/projects" element={<ProjectListPage />} />

                {/* Individual Project Hub & Sub-pages */}
                <Route path="/projects/:projectId" element={<ProjectOverviewPage />} />
                <Route path="/projects/:projectId/evaluations" element={<EvaluationsListPage />} />
                <Route
                  path="/projects/:projectId/evaluations/:evaluationId"
                  element={<EvaluationDetailPage />}
                />
                <Route path="/projects/:projectId/datasets" element={<DatasetsPage />} />
                <Route path="/projects/:projectId/guardrails" element={<GuardrailsPage />} />
                <Route path="/projects/:projectId/documents" element={<DocumentsPage />} />
                <Route path="/projects/:projectId/playground" element={<PlaygroundPage />} />
                <Route path="/projects/:projectId/settings" element={<ProjectSettingsPage />} />
              </Route>
            </Route>

            {/* Catch-all route */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
