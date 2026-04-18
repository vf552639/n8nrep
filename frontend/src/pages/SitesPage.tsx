import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { sitesApi } from "@/api/sites";
import { templatesApi } from "@/api/templates";
import { SiteCreateInput } from "@/types/site";
import { ReactTable } from "@/components/common/ReactTable";
import { Plus, Globe, X, Trash2 } from "lucide-react";
import { normalizeLanguageDisplay } from "@/lib/languageDisplay";

export default function SitesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const { data: sites, isLoading } = useQuery({
    queryKey: ["sites"],
    queryFn: async () => {
      return sitesApi.getAll();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => sitesApi.delete(id),
    onSuccess: () => {
      toast.success("Site deleted");
      queryClient.invalidateQueries({ queryKey: ["sites"] });
      setDeleteId(null);
    },
    onError: (error: unknown) => {
      const ax = error as { response?: { data?: { detail?: string | string[] } } };
      const d = ax.response?.data?.detail;
      const msg =
        typeof d === "string"
          ? d
          : Array.isArray(d)
            ? d.join(" ")
            : "Failed to delete site";
      toast.error(msg);
    },
  });

  const columns = [
    { 
      accessorKey: "name", 
      header: "Site Name", 
      cell: ({ row }: any) => <div className="font-semibold text-slate-800 flex items-center gap-2"><Globe className="w-4 h-4 text-slate-400"/> {row.original.name}</div> 
    },
    { 
      accessorKey: "domain", 
      header: "Domain", 
      cell: ({ row }: any) => <span className="text-blue-600 font-medium hover:underline cursor-pointer">{row.original.domain}</span> 
    },
    { accessorKey: "country", header: "Country" },
    { accessorKey: "language", header: "Language" },
    {
      accessorKey: "template_name",
      header: "Template",
      cell: ({ row }: any) => (
        <span className="text-slate-600">{row.original.template_name || "—"}</span>
      ),
    },
    { 
      accessorKey: "is_active", 
      header: "Status", 
      cell: ({ row }: any) => (
        <span className={`px-2 py-1 rounded text-xs font-semibold ${row.original.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-800'}`}>
          {row.original.is_active ? "Active" : "Inactive"}
        </span>
      ) 
    },
    {
      id: "actions",
      header: "Actions",
      enableSorting: false,
      meta: { tdClassName: "w-12 min-w-[3rem] text-right" },
      cell: ({ row }: any) => (
        <button
          type="button"
          title="Delete site"
          className="p-1.5 rounded-md text-red-600 hover:bg-red-50 hover:text-red-700 transition-colors"
          onClick={(e) => {
            e.stopPropagation();
            setDeleteId(row.original.id);
          }}
        >
          <Trash2 className="w-4 h-4" />
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-5 rounded-xl border shadow-sm">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 border-l-4 border-blue-500 pl-3">Sites</h1>
          <p className="text-sm text-slate-500 mt-1 pl-4">Target sites (domain, GEO, language). Assign an HTML template per site.</p>
        </div>
        <button 
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors text-sm font-medium shadow-sm w-full sm:w-auto"
        >
          <Plus className="w-4 h-4" /> Add Site
        </button>
      </div>

      <ReactTable 
        columns={columns as any} 
        data={sites || []} 
        isLoading={isLoading} 
        onRowClick={(site: any) => navigate(`/sites/${site.id}`)}
      />

      {isCreateOpen && (
        <CreateSiteModal onClose={() => setIsCreateOpen(false)} />
      )}

      {deleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-4 border">
            <h2 className="text-lg font-semibold text-slate-900">Delete site?</h2>
            <p className="text-sm text-slate-600">Вы уверены? Сайт будет удалён (если нет задач и проектов).</p>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-lg"
                onClick={() => setDeleteId(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg disabled:opacity-50"
                disabled={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate(deleteId)}
              >
                {deleteMutation.isPending ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function CreateSiteModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const { data: authors } = useQuery({
    queryKey: ["authors"],
    queryFn: () => import("@/api/authors").then((m) => m.authorsApi.getAll()),
  });

  const { data: tplList } = useQuery({
    queryKey: ["html-templates"],
    queryFn: () => templatesApi.getAll(),
  });

  const countries = Array.from(
    new Set((authors || []).map((a: { country: string }) => a.country).filter(Boolean))
  ).sort();
  const languages = Array.from(
    new Set(
      (authors || []).map((a: { language: string }) =>
        normalizeLanguageDisplay(String(a.language || ""))
      ).filter(Boolean)
    )
  ).sort();

  const [formData, setFormData] = useState({
    name: "",
    domain: "",
    country: "",
    language: "",
    template_id: "" as string | "",
  });

  const mutation = useMutation({
    mutationFn: (data: SiteCreateInput) => sitesApi.create(data),
    onSuccess: () => {
      toast.success("Site created successfully");
      queryClient.invalidateQueries({ queryKey: ["sites"] });
      onClose();
    },
    onError: () => toast.error("Failed to create site")
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name || !formData.domain || !formData.country || !formData.language) {
      toast.error("Name, Domain, Country, and Language are required");
      return;
    }
    mutation.mutate({
      name: formData.name,
      domain: formData.domain,
      country: formData.country,
      language: formData.language,
      template_id: formData.template_id || undefined,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
        <div className="px-6 py-4 border-b bg-slate-50 flex justify-between items-center">
            <h2 className="text-lg font-bold text-slate-900">Add New Site</h2>
            <button onClick={onClose} className="p-1 hover:bg-slate-200 rounded text-slate-500"><X className="w-5 h-5"/></button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
           <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Site Name *</label>
              <input 
                required
                type="text" 
                value={formData.name}
                onChange={e => setFormData({...formData, name: e.target.value})}
                className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm" 
                placeholder="e.g. My Awesome Blog" 
              />
           </div>
           <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Domain *</label>
              <input 
                required
                type="text" 
                value={formData.domain}
                onChange={e => setFormData({...formData, domain: e.target.value})}
                className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm" 
                placeholder="e.g. awesome-blog.com" 
              />
           </div>
           <div className="grid grid-cols-2 gap-4">
             <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Country *</label>
                <select
                  required
                  className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm bg-white"
                  value={formData.country}
                  onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                >
                  <option value="" disabled>
                    Select country...
                  </option>
                  {(countries as string[]).map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
             </div>
             <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Language *</label>
                <select
                  required
                  className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm bg-white"
                  value={formData.language}
                  onChange={(e) => setFormData({ ...formData, language: e.target.value })}
                >
                  <option value="" disabled>
                    Select language...
                  </option>
                  {(languages as string[]).map((l) => (
                    <option key={l} value={l}>
                      {l}
                    </option>
                  ))}
                </select>
             </div>
           </div>
           <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">HTML Template</label>
              <select
                className="w-full border outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3 py-2 text-sm bg-white"
                value={formData.template_id}
                onChange={(e) => setFormData({ ...formData, template_id: e.target.value })}
              >
                <option value="">— Optional —</option>
                {(tplList || []).map((t: { id: string; name: string }) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
           </div>
           <div className="flex justify-end gap-3 mt-8 pt-4 border-t">
             <button 
               type="button"
               onClick={onClose}
               className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg text-sm font-medium transition-colors"
             >
               Cancel
             </button>
             <button 
               type="submit"
               disabled={mutation.isPending}
               className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium transition-colors shadow-sm disabled:opacity-50"
             >
               {mutation.isPending ? "Saving..." : "Save Site"}
             </button>
           </div>
        </form>
      </div>
    </div>
  );
}
