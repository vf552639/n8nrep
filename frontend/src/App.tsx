import { Suspense, lazy } from "react";
import { Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import LoadingSpinner from "@/components/common/LoadingSpinner";
import { RouteErrorBoundary } from "@/components/common/RouteErrorBoundary";

// Layouts
import MainLayout from "@/components/layout/MainLayout";

// Lazy Pages
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const TasksPage = lazy(() => import("./pages/TasksPage"));
const TaskDetailPage = lazy(() => import("./pages/TaskDetailPage"));
const ArticlesPage = lazy(() => import("./pages/ArticlesPage"));
const ArticleDetailPage = lazy(() => import("./pages/ArticleDetailPage"));
const SitesPage = lazy(() => import("./pages/SitesPage"));
const SiteDetailPage = lazy(() => import("./pages/SiteDetailPage"));
const TemplatesPage = lazy(() => import("./pages/TemplatesPage"));
const LegalPagesPage = lazy(() => import("./pages/LegalPagesPage"));
const AuthorsPage = lazy(() => import("./pages/AuthorsPage"));
const PromptsPage = lazy(() => import("./pages/PromptsPage"));
const BlueprintsPage = lazy(() => import("./pages/BlueprintsPage"));
const ProjectsPage = lazy(() => import("./pages/ProjectsPage"));
const ProjectDetailPage = lazy(() => import("./pages/ProjectDetailPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const LogsPage = lazy(() => import("./pages/LogsPage"));
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Toaster position="top-right" />
      <Suspense fallback={<div className="flex h-screen w-full items-center justify-center"><LoadingSpinner size="lg" /></div>}>
        <RouteErrorBoundary>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="tasks" element={<TasksPage />} />
            <Route path="tasks/:id" element={<TaskDetailPage />} />
            <Route path="articles" element={<ArticlesPage />} />
            <Route path="articles/:id" element={<ArticleDetailPage />} />
            <Route path="templates" element={<TemplatesPage />} />
            <Route path="sites" element={<SitesPage />} />
            <Route path="sites/:id" element={<SiteDetailPage />} />
            <Route path="legal-pages" element={<LegalPagesPage />} />
            <Route path="authors" element={<AuthorsPage />} />
            <Route path="prompts" element={<PromptsPage />} />
            <Route path="blueprints" element={<BlueprintsPage />} />
            <Route path="projects" element={<ProjectsPage />} />
            <Route path="projects/:id" element={<ProjectDetailPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="logs" element={<LogsPage />} />
            <Route path="*" element={<div className="p-8 text-center text-slate-500">404 - Page not found</div>} />
          </Route>
        </Routes>
        </RouteErrorBoundary>
      </Suspense>
    </QueryClientProvider>
  );
}

export default App;
