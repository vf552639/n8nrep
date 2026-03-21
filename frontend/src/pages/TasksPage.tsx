import { useState, useRef, useMemo, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { tasksApi } from "@/api/tasks";
import { ReactTable } from "@/components/common/ReactTable";
import StatusBadge from "@/components/common/StatusBadge";
import { Plus, Upload, Play, X, Search, Filter } from "lucide-react";
import QueueControls from "@/components/tasks/QueueControls";
import { sitesApi } from "@/api/sites";

export default function TasksPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [siteFilter, setSiteFilter] = useState("");
  const [search, setSearch] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());
  const selectAllRef = useRef<HTMLInputElement>(null);

  const { data: tasks, isLoading } = useQuery({
    queryKey: ["tasks", { status: statusFilter, site: siteFilter }],
    queryFn: async () => {
      // Assuming backend supports these filters in `getAll`
      return tasksApi.getAll({ status: statusFilter || undefined, limit: 1000 });
    },
  });

  const { data: sites } = useQuery({
    queryKey: ["sites"],
    queryFn: () => sitesApi.getAll(),
  });

  const handleStartNext = async () => {
    try {
      await tasksApi.startNext();
      toast.success("Started next task in queue");
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    } catch {
      toast.error("Failed to start next task");
    }
  };

  const handleStartAll = async () => {
    try {
      await tasksApi.startAll();
      toast.success("Started all pending tasks");
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    } catch {
      toast.error("Failed to start all tasks");
    }
  };

  const startSelectedMutation = useMutation({
    mutationFn: (ids: string[]) => tasksApi.startSelected(ids),
    onSuccess: (data) => {
      toast.success(data.msg || "Started selected tasks");
      setSelectedIds(new Set());
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: () => toast.error("Failed to start selected tasks"),
  });

  const filteredTasks = useMemo(() => {
    return (tasks || []).filter((t) => {
      if (siteFilter && t.target_site_id !== siteFilter) return false;
      if (search && !t.main_keyword.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [tasks, siteFilter, search]);

  const pendingInView = useMemo(
    () => filteredTasks.filter((t) => t.status === "pending"),
    [filteredTasks]
  );

  useEffect(() => {
    const el = selectAllRef.current;
    if (!el) return;
    const some = pendingInView.some((t) => selectedIds.has(t.id));
    const all = pendingInView.length > 0 && pendingInView.every((t) => selectedIds.has(t.id));
    el.indeterminate = some && !all;
  }, [pendingInView, selectedIds]);

  const toggleSelectAllPending = useCallback(() => {
    const ids = pendingInView.map((t) => t.id);
    const allSelected = ids.length > 0 && ids.every((id) => selectedIds.has(id));
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (allSelected) {
        ids.forEach((id) => next.delete(id));
      } else {
        ids.forEach((id) => next.add(id));
      }
      return next;
    });
  }, [pendingInView, selectedIds]);

  const columns = useMemo(
    () => [
    {
      id: "select",
      enableSorting: false,
      meta: { tdClassName: "w-10 min-w-[2.5rem] align-middle" },
      header: () => (
        <input
          ref={selectAllRef}
          type="checkbox"
          className="rounded border-slate-300 text-blue-600"
          checked={pendingInView.length > 0 && pendingInView.every((t) => selectedIds.has(t.id))}
          onChange={toggleSelectAllPending}
          title="Select all pending"
          aria-label="Select all pending tasks"
        />
      ),
      cell: ({ row }: any) => {
        const t = row.original;
        if (t.status !== "pending") {
          return <span className="inline-block w-5" aria-hidden />;
        }
        return (
          <input
            type="checkbox"
            className="rounded border-slate-300 text-blue-600"
            checked={selectedIds.has(t.id)}
            title="Select task"
            onClick={(e) => e.stopPropagation()}
            onChange={(e) => {
              e.stopPropagation();
              const checked = e.target.checked;
              setSelectedIds((prev) => {
                const next = new Set(prev);
                if (checked) next.add(t.id);
                else next.delete(t.id);
                return next;
              });
            }}
          />
        );
      },
    },
    { accessorKey: "main_keyword", header: "Keyword" },
    { accessorKey: "country", header: "Country" },
    { 
      accessorKey: "status", 
      header: "Status",
      cell: ({ row }: any) => <StatusBadge status={row.original.status} />
    },
    { 
      accessorKey: "progress", 
      header: "Progress",
      cell: ({ row }: any) => <span className="text-slate-500 font-medium">{row.original.progress || 0}%</span>
    },
    { 
      accessorKey: "total_cost", 
      header: "Cost",
      cell: ({ row }: any) => <span className="text-slate-500 font-mono">${row.original.total_cost?.toFixed(4) || "0.0000"}</span>
    },
    { 
      accessorKey: "created_at", 
      header: "Date",
      cell: ({ row }: any) => new Date(row.original.created_at).toLocaleString()
    },
  ],
  [pendingInView, selectedIds, toggleSelectAllPending]
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Tasks</h1>
        <div className="flex flex-wrap gap-2">
          <button 
            onClick={() => setIsImportOpen(true)}
            className="flex items-center gap-2 bg-white hover:bg-slate-50 text-slate-800 px-4 py-2 rounded-lg transition-colors text-sm font-medium border shadow-sm"
          >
            <Upload className="w-4 h-4" /> Import CSV
          </button>
          <button 
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors text-sm font-medium shadow-sm"
          >
            <Plus className="w-4 h-4" /> Create Task
          </button>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-center bg-white p-4 rounded-xl border shadow-sm">
        <div className="flex-1 flex gap-3 flex-wrap items-center">
            <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input 
                    type="text" 
                    placeholder="Search keyword..." 
                    className="pl-9 pr-4 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none w-64"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
            </div>
            <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-slate-400" />
                <select 
                    className="border bg-slate-50 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                >
                    <option value="">All Statuses</option>
                    <option value="pending">Pending</option>
                    <option value="processing">Processing</option>
                    <option value="completed">Completed</option>
                    <option value="failed">Failed</option>
                </select>
                <select 
                    className="border bg-slate-50 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none max-w-xs"
                    value={siteFilter}
                    onChange={(e) => setSiteFilter(e.target.value)}
                >
                    <option value="">All Sites</option>
                    {sites?.map((s: any) => (
                        <option key={s.id} value={s.id}>{s.domain}</option>
                    ))}
                </select>
            </div>
        </div>
        <div className="hidden lg:block w-px h-8 bg-slate-200"></div>
        <div className="flex items-center gap-2">
          <button onClick={handleStartNext} className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 text-blue-700 hover:bg-blue-100 rounded-lg text-sm transition-colors border border-blue-200 font-medium">
            <Play className="w-4 h-4" /> Start Next
          </button>
          <button onClick={handleStartAll} className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 rounded-lg text-sm transition-colors border border-emerald-200 font-medium">
            <Play className="w-4 h-4" /> Start All
          </button>
          <button
            type="button"
            disabled={selectedIds.size === 0 || startSelectedMutation.isPending}
            onClick={() => startSelectedMutation.mutate(Array.from(selectedIds))}
            className="flex items-center gap-1.5 rounded-lg border border-violet-200 bg-violet-50 px-3 py-1.5 text-sm font-medium text-violet-800 transition-colors hover:bg-violet-100 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Play className="w-4 h-4" /> Start Selected ({selectedIds.size})
          </button>
          <QueueControls />
        </div>
      </div>

      <ReactTable 
        columns={columns as any} 
        data={filteredTasks} 
        isLoading={isLoading} 
        onRowClick={(task: any) => navigate(`/tasks/${task.id}`)}
      />

      {isCreateOpen && (
        <CreateTaskModal onClose={() => setIsCreateOpen(false)} />
      )}

      {isImportOpen && (
        <ImportTasksModal onClose={() => setIsImportOpen(false)} />
      )}
    </div>
  );
}

function CreateTaskModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const { data: authors } = useQuery({
    queryKey: ["authors"],
    queryFn: () => import("@/api/authors").then(m => m.authorsApi.getAll()),
  });

  const [formData, setFormData] = useState({
    main_keyword: "",
    additional_keywords: "",
    country: "",
    language: "",
    target_site: "",
    author_id: "" as string | null,
    page_type: "article"
  });

  // Extract unique countries and languages from authors
  const countries = Array.from(new Set((authors || []).map((a: any) => a.country).filter(Boolean))).sort();
  const languages = Array.from(new Set((authors || []).map((a: any) => a.language).filter(Boolean))).sort();

  const filteredAuthors = (authors || []).filter(
    (a: any) => a.country === formData.country && a.language === formData.language
  );

  const mutation = useMutation({
    mutationFn: (data: any) => {
      const payload = { ...data };
      if (!payload.author_id) {
          payload.author_id = null;
      }
      return tasksApi.create(payload);
    },
    onSuccess: () => {
      toast.success("Task created successfully");
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      onClose();
    },
    onError: () => toast.error("Failed to create task")
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.main_keyword || !formData.target_site || !formData.country || !formData.language) {
        toast.error("Please fill required fields: Keyword, Site, Country, Language");
        return;
    }
    mutation.mutate(formData);
  };

  return (
    <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl overflow-hidden border border-slate-200 flex flex-col max-h-[90vh]">
        <div className="px-6 py-4 border-b flex justify-between items-center bg-slate-50/50 shrink-0">
          <h2 className="text-lg font-bold text-slate-800">Create New Task</h2>
          <button onClick={onClose} className="p-1 hover:bg-slate-200 rounded-md transition-colors text-slate-500 hover:text-slate-700"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-6 overflow-y-auto flex-1">
          <form id="create-task-form" onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Keyword *</label>
              <input 
                required
                className="w-full px-3 py-2 border rounded-lg outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500" 
                value={formData.main_keyword} 
                onChange={e => setFormData({...formData, main_keyword: e.target.value})} 
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Additional Keywords</label>
              <textarea 
                className="w-full px-3 py-2 border rounded-lg outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none h-16" 
                placeholder="Comma separated secondary keywords..."
                value={formData.additional_keywords} 
                onChange={e => setFormData({...formData, additional_keywords: e.target.value})} 
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Country *</label>
                <select 
                  required
                  className="w-full px-3 py-2 border rounded-lg outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 bg-white" 
                  value={formData.country} 
                  onChange={e => setFormData({...formData, country: e.target.value, author_id: ""})}
                >
                  <option value="" disabled>Select country...</option>
                  {(countries as string[]).map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Language *</label>
                <select 
                  required
                  className="w-full px-3 py-2 border rounded-lg outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 bg-white" 
                  value={formData.language} 
                  onChange={e => setFormData({...formData, language: e.target.value, author_id: ""})}
                >
                  <option value="" disabled>Select language...</option>
                  {(languages as string[]).map(l => <option key={l} value={l}>{l}</option>)}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Target Site *</label>
                <input 
                  required
                  type="text"
                  placeholder="e.g. example.com"
                  className="w-full px-3 py-2 border rounded-lg outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 bg-white" 
                  value={formData.target_site} 
                  onChange={e => setFormData({...formData, target_site: e.target.value})}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Author</label>
                <select 
                  className="w-full px-3 py-2 border rounded-lg outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 bg-white disabled:bg-slate-50 disabled:text-slate-400" 
                  value={formData.author_id || ""} 
                  onChange={e => setFormData({...formData, author_id: e.target.value || null})}
                  disabled={!formData.country || !formData.language}
                >
                  <option value="">Auto (by GEO/Language)</option>
                  {filteredAuthors?.map((a: any) => (
                     <option key={a.id} value={a.id}>{a.author || a.name || a.id}</option>
                  ))}
                </select>
                {(!formData.country || !formData.language) && (
                   <p className="text-xs text-slate-500 mt-1">Select Country and Language first</p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Page Type</label>
              <select 
                className="w-full px-3 py-2 border rounded-lg outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 bg-white" 
                value={formData.page_type} 
                onChange={e => setFormData({...formData, page_type: e.target.value})}
              >
                <option value="article">Article</option>
                <option value="homepage">Homepage</option>
                <option value="category">Category</option>
              </select>
            </div>
          </form>
        </div>
        <div className="px-6 py-4 flex justify-end gap-3 border-t bg-slate-50 shrink-0">
          <button type="button" onClick={onClose} className="px-4 py-2 font-medium text-slate-600 hover:bg-slate-200 rounded-lg transition-colors">Cancel</button>
          <button type="submit" form="create-task-form" disabled={mutation.isPending} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors shadow-sm disabled:opacity-50">
            {mutation.isPending ? "Creating..." : "Create Task"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ImportTasksModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);

  const mutation = useMutation({
    mutationFn: (f: File) => {
      const data = new FormData();
      data.append("file", f);
      return tasksApi.bulkImport(data);
    },
    onSuccess: (res: any) => {
      toast.success(`Imported ${res.detail || "tasks"} successfully`);
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      onClose();
    },
    onError: () => toast.error("Failed to import tasks")
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
        toast.error("Please select a CSV file");
        return;
    }
    mutation.mutate(file);
  };

  return (
    <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden border border-slate-200">
        <div className="px-6 py-4 border-b flex justify-between items-center bg-slate-50/50">
          <h2 className="text-lg font-bold text-slate-800">Import Tasks via CSV</h2>
          <button onClick={onClose} className="p-1 hover:bg-slate-200 rounded-md transition-colors text-slate-500 hover:text-slate-700"><X className="w-5 h-5" /></button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <p className="text-sm text-slate-500 mb-4">Upload a CSV file with columns: <code>keyword</code>, <code>country</code>, <code>language</code>, <code>target_site_id</code>.</p>
          <div 
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-slate-300 hover:border-blue-500 hover:bg-blue-50 transition-colors rounded-xl p-8 text-center cursor-pointer flex flex-col items-center justify-center"
          >
             <Upload className="w-8 h-8 text-slate-400 mb-3" />
             {file ? (
                 <span className="font-medium text-blue-700">{file.name}</span>
             ) : (
                 <>
                   <span className="font-medium text-slate-700">Click to browse or drag and drop</span>
                   <span className="text-xs text-slate-500 mt-1">CSV files only</span>
                 </>
             )}
             <input 
               type="file" 
               accept=".csv" 
               className="hidden" 
               ref={fileInputRef}
               onChange={(e) => setFile(e.target.files?.[0] || null)}
             />
          </div>
          <div className="pt-4 flex justify-end gap-3">
            <button type="button" onClick={onClose} className="px-4 py-2 font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors">Cancel</button>
            <button type="submit" disabled={mutation.isPending || !file} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors shadow-sm disabled:opacity-50">
              {mutation.isPending ? "Importing..." : "Run Import"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
