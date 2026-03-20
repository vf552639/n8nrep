import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import api from "@/api/client";
import { Site } from "@/types/site";
import { ArrowLeft, Save } from "lucide-react";

export default function SiteDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // Fetch all sites and find the correct one
  const { data: sites, isLoading } = useQuery({
    queryKey: ["sites"],
    queryFn: async () => {
      const res = await api.get<Site[]>("/sites");
      return res.data;
    },
  });

  const site = sites?.find(s => s.id === id);

  // Fetch templates for this site
  const { data: templates } = useQuery({
    queryKey: ["site-templates", id],
    queryFn: async () => {
      const res = await api.get<any[]>(`/sites/${id}/templates`);
      return res.data;
    },
    enabled: !!id,
  });

  const [activeTab, setActiveTab] = useState("templates");

  if (isLoading) return <div className="p-6 text-slate-500">Loading site details...</div>;
  if (!site) return <div className="p-6 text-red-500">Site not found</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-white p-4 rounded-lg shadow-sm border">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate("/sites")}
            className="p-2 hover:bg-slate-100 rounded-md transition-colors text-slate-500"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">{site.name}</h1>
            <div className="text-sm text-slate-500 mt-1 flex gap-3">
               <span>Domain: <a href={`https://${site.domain}`} className="text-blue-600 hover:underline" target="_blank" rel="noreferrer">{site.domain}</a></span>
               <span>| Country: {site.country}</span>
               <span>| Lang: {site.language}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white border rounded-lg shadow-sm overflow-hidden">
        <div className="flex border-b">
          <button 
            className={`px-4 py-3 text-sm font-medium text-slate-700 ${activeTab === 'templates' ? 'border-b-2 border-blue-600' : 'hover:bg-slate-50'}`}
            onClick={() => setActiveTab('templates')}
          >
            HTML Templates
          </button>
          <button 
            className={`px-4 py-3 text-sm font-medium text-slate-700 ${activeTab === 'settings' ? 'border-b-2 border-blue-600' : 'hover:bg-slate-50'}`}
            onClick={() => setActiveTab('settings')}
          >
            Site Settings
          </button>
        </div>

        <div className="p-6">
          {activeTab === 'templates' && (
             <div className="space-y-6">
               <div className="flex justify-between items-center">
                 <h2 className="text-lg font-semibold border-b pb-2 mb-4 w-full">Manage Templates</h2>
               </div>
               {templates?.length === 0 ? (
                 <div className="text-center py-12 border-2 border-dashed rounded-lg">
                   <p className="text-slate-500">No templates found for this site.</p>
                   <button className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 shadow-sm text-sm">Create First Template</button>
                 </div>
               ) : (
                 <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                   {templates?.map((t) => (
                      <div key={t.id} className="border rounded-md p-4 hover:border-blue-300 transition-colors shadow-sm">
                        <h3 className="font-semibold text-slate-800">{t.template_name}</h3>
                        <p className="text-xs text-slate-500 mt-1">Used {t.usage_count || 0} times</p>
                        <div className="mt-4 flex gap-2">
                           <button className="text-xs px-2 py-1 bg-blue-50 text-blue-700 rounded hover:bg-blue-100">Edit HTML</button>
                           <button className="text-xs px-2 py-1 bg-red-50 text-red-700 rounded hover:bg-red-100">Delete</button>
                        </div>
                      </div>
                   ))}
                   <div className="border border-dashed rounded-md p-4 flex items-center justify-center cursor-pointer hover:bg-slate-50 transition-colors group">
                     <span className="text-slate-400 font-medium group-hover:text-blue-600"> + Add Template</span>
                   </div>
                 </div>
               )}
             </div>
          )}
          {activeTab === 'settings' && (
             <div>
               <h2 className="text-lg font-semibold border-b pb-2 mb-4">Site Information</h2>
               <p className="text-sm text-slate-600">Update general site information here.</p>
               {/* Stub for settings form */}
               <div className="mt-4 flex">
                  <button className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 shadow-sm"><Save className="w-4 h-4" /> Save Changes</button>
               </div>
             </div>
          )}
        </div>
      </div>
    </div>
  );
}
