import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { tasksApi } from "@/api/tasks";
import StatusBadge from "@/components/common/StatusBadge";
import StepMonitor from "@/components/tasks/StepMonitor";
import ImageReviewPanel from "@/components/tasks/ImageReviewPanel";
import { Info, XCircle } from "lucide-react";

type LogEntry = {
  ts?: string;
  msg?: string;
  level?: string;
  step?: string | null;
};

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("pipeline");
  const [reviewView, setReviewView] = useState<"preview" | "source">("preview");

  const { data: task, isLoading } = useQuery({
    queryKey: ["task", id],
    queryFn: () => tasksApi.getOne(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "processing" || status === "pending" ? 3000 : false;
    },
  });

  const approveMutation = useMutation({
    mutationFn: () => tasksApi.approve(id!),
    onSuccess: () => {
      toast.success("Approved! Pipeline resumed.");
      queryClient.invalidateQueries({ queryKey: ["task", id] });
      queryClient.invalidateQueries({ queryKey: ["task-steps", id] });
      queryClient.refetchQueries({ queryKey: ["task", id] });
      queryClient.refetchQueries({ queryKey: ["task-steps", id] });
      setActiveTab("pipeline");
    },
    onError: (e: any) => {
      toast.error(e?.response?.data?.detail || "Failed to approve");
    },
  });

  const isWaiting = task?.step_results?.waiting_for_approval === true;
  const isImagePaused = task?.step_results?._pipeline_pause?.active && task?.step_results?._pipeline_pause?.reason === "image_review";
  const hasDraft = task?.step_results?.primary_generation?.status === "completed";
  const hasImages = task?.step_results?.image_generation?.status === "completed";
  const draftHtml: string = task?.step_results?.primary_generation?.result || "";
  const wordCount = draftHtml
    ? draftHtml.replace(/<[^>]*>/g, " ").split(/\s+/).filter(Boolean).length
    : 0;

  const { data: imageData, refetch: refetchImages } = useQuery({
    queryKey: ["task-images", id],
    queryFn: () => tasksApi.getImages(id!),
    enabled: !!id && !!hasImages,
  });

  // Auto-switch to review tab when waiting for approval
  useEffect(() => {
    if (isWaiting && activeTab !== "review") {
      setActiveTab("review");
    }
    if (isImagePaused && activeTab !== "images") {
      setActiveTab("images");
    }
  }, [isWaiting, isImagePaused]);

  const handleForceAction = async (action: "complete" | "fail") => {
    try {
      if (!id) return;
      await tasksApi.forceStatus(id, action);
      toast.success(`Task forced to ${action === "complete" ? "Completed" : "Failed"}`);
      queryClient.invalidateQueries({ queryKey: ["task", id] });
    } catch {
      toast.error("Failed to force action. Check console.");
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center p-6 text-slate-500">Loading task details...</div>
    );
  }
  if (!task) return <div className="p-6 text-red-500">Task not found</div>;

  const tabs = [
    { id: "pipeline", label: "Pipeline Execution" },
    ...(hasImages || isImagePaused ? [{ id: "images", label: "🖼️ Image Review" }] : []),
    ...(hasDraft || isWaiting ? [{ id: "review", label: "📝 Article Review" }] : []),
    { id: "logs", label: "Execution Logs" },
  ];

  const logs: LogEntry[] = Array.isArray(task.logs) ? task.logs : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Task: {task.main_keyword}</h1>
          <div className="mt-1 font-mono text-sm text-slate-500">ID: {task.id}</div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex gap-2 rounded-md border bg-slate-50 px-3 py-1.5 text-sm">
            <button
              type="button"
              onClick={() => handleForceAction("complete")}
              className="flex items-center gap-1 font-medium text-emerald-700 hover:text-emerald-800 hover:underline"
            >
              Force Complete
            </button>
            <span className="text-slate-300">|</span>
            <button
              type="button"
              onClick={() => handleForceAction("fail")}
              className="flex items-center gap-1 font-medium text-red-700 hover:text-red-800 hover:underline"
            >
              Force Fail
            </button>
          </div>
          <StatusBadge status={task.status} />
        </div>
      </div>

      <div className="mt-4 flex gap-2 overflow-x-auto border-b">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`whitespace-nowrap border-b-2 px-4 pb-3 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "border-blue-600 text-blue-600"
                : "rounded-t-lg border-transparent text-slate-500 hover:bg-slate-50 hover:text-slate-800"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          {activeTab === "pipeline" && (
            <div className="animate-in fade-in slide-in-from-bottom-2 space-y-4 rounded-xl border bg-white p-6 shadow-sm duration-300">
              {(() => {
                const pause = (task.step_results as any)?._pipeline_pause;
                const approved = (task.step_results as any)?._images_approved;
                if (pause?.active && pause?.reason === "image_review" && !approved) {
                  return (
                    <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 flex items-center justify-between gap-4">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">🖼️</span>
                        <div>
                          <p className="font-semibold text-amber-800">Pipeline paused — Images ready for review</p>
                          <p className="text-sm text-amber-600">
                            Midjourney finished generating images. Review and approve them to continue.
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => setActiveTab("images")}
                        className="bg-amber-500 hover:bg-amber-600 text-white px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap"
                      >
                        Review Images →
                      </button>
                    </div>
                  );
                }
                return null;
              })()}
              <StepMonitor taskId={task.id} isActive={task.status === "processing"} />
            </div>
          )}

          {activeTab === "images" && (
            <div className="animate-in fade-in slide-in-from-bottom-2 rounded-xl border bg-white p-6 shadow-sm duration-300">
              <h2 className="mb-4 text-lg font-semibold text-slate-800">Image Review</h2>
              {imageData && imageData.images.length > 0 ? (
                <ImageReviewPanel
                  taskId={task.id}
                  images={imageData.images}
                  paused={imageData.paused}
                  onRefresh={refetchImages}
                />
              ) : (
                <div className="text-sm text-slate-400 italic text-center py-8">
                  No images generated for this task.
                </div>
              )}
            </div>
          )}

          {activeTab === "review" && (
            <div className="animate-in fade-in slide-in-from-bottom-2 rounded-xl border bg-white shadow-sm duration-300 flex flex-col">
              {/* Approval Banner */}
              {isWaiting && (
                <div className="flex items-center gap-3 px-5 py-3 bg-amber-50 border-b border-amber-200">
                  <span className="text-lg">🛑</span>
                  <div>
                    <p className="font-semibold text-amber-900 text-sm">TEST MODE: Pipeline paused</p>
                    <p className="text-amber-700 text-xs">Waiting for manual approval after Primary Generation</p>
                  </div>
                </div>
              )}

              {/* Preview / Source toggle */}
              <div className="flex gap-1 border-b px-5 pt-3">
                {(["preview", "source"] as const).map((v) => (
                  <button
                    key={v}
                    onClick={() => setReviewView(v)}
                    className={`pb-2 px-3 text-sm font-medium capitalize transition-colors border-b-2 ${
                      reviewView === v
                        ? "border-blue-600 text-blue-600"
                        : "border-transparent text-slate-500 hover:text-slate-800"
                    }`}
                  >
                    {v}
                  </button>
                ))}
              </div>

              {/* Content area */}
              {draftHtml ? (
                reviewView === "preview" ? (
                  <iframe
                    srcDoc={draftHtml}
                    className="w-full border-none flex-1 min-h-[600px] bg-white"
                    sandbox="allow-same-origin"
                  />
                ) : (
                  <div className="overflow-auto flex-1 bg-slate-900 min-h-[600px] font-mono text-sm p-6">
                    <pre className="whitespace-pre-wrap text-emerald-400">{draftHtml}</pre>
                  </div>
                )
              ) : (
                <div className="flex items-center justify-center min-h-[300px] text-slate-400 text-sm italic">
                  No draft content available yet
                </div>
              )}

              {/* Footer with approve button */}
              {isWaiting && (
                <div className="flex items-center justify-between px-5 py-4 border-t bg-slate-50">
                  <span className="text-sm text-slate-500">
                    ~<span className="font-mono font-medium text-slate-700">{wordCount}</span> words
                  </span>
                  <button
                    onClick={() => approveMutation.mutate()}
                    disabled={approveMutation.isPending}
                    className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white font-medium text-sm rounded-lg transition-colors shadow-sm"
                  >
                    {approveMutation.isPending ? (
                      <>
                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Approving…
                      </>
                    ) : (
                      <>✅ Approve & Continue Pipeline</>
                    )}
                  </button>
                </div>
              )}
            </div>
          )}

          {activeTab === "logs" && (
            <div className="animate-in fade-in slide-in-from-bottom-2 rounded-xl border bg-white p-6 shadow-sm duration-300">
              <h2 className="mb-4 text-lg font-semibold text-slate-800">Task execution logs</h2>
              <div className="h-[500px] overflow-auto rounded-lg bg-[#1e1e1e] p-4 font-mono text-sm">
                {logs.length > 0 ? (
                  logs.map((log, i) => {
                    const lvl = (log.level || "info").toLowerCase();
                    const isErr = lvl === "error";
                    return (
                      <div key={i} className="mb-1.5 flex flex-wrap gap-x-2 leading-relaxed">
                        <span className="shrink-0 text-slate-500">
                          [{log.ts || ""}]
                        </span>
                        {lvl === "error" ? (
                          <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-red-400" aria-hidden />
                        ) : (
                          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" aria-hidden />
                        )}
                        {log.step && (
                          <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-slate-200">
                            {log.step}
                          </span>
                        )}
                        <span
                          className={
                            isErr ? "text-red-300" : "text-slate-300"
                          }
                        >
                          {log.msg ?? ""}
                        </span>
                      </div>
                    );
                  })
                ) : (
                  <div className="italic text-slate-500">
                    No logs for this task yet. Logs are written as the pipeline runs.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="rounded-xl border bg-white p-6 shadow-sm">
            <h2 className="mb-4 border-b pb-4 text-lg font-semibold text-slate-800">Task details</h2>
            <ul className="space-y-4 text-sm">
              <li className="flex items-center justify-between">
                <span className="text-slate-500">Country:</span>
                <span className="rounded bg-slate-100 px-2 py-1 font-medium">{task.country}</span>
              </li>
              <li className="flex items-center justify-between">
                <span className="text-slate-500">Language:</span>
                <span className="rounded bg-slate-100 px-2 py-1 font-medium">{task.language}</span>
              </li>
              <li className="flex items-center justify-between">
                <span className="text-slate-500">Cost:</span>
                <span className="font-mono font-medium text-emerald-600">
                  ${task.total_cost?.toFixed(4) || "0.0000"}
                </span>
              </li>
              <li className="flex items-center justify-between">
                <span className="text-slate-500">Created at:</span>
                <span className="font-medium text-slate-700">{new Date(task.created_at).toLocaleString()}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
