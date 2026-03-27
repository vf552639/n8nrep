import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { tasksApi } from "@/api/tasks";
import { RefreshCw, Check, X, Eye, EyeOff } from "lucide-react";

interface ImageData {
  id: string;
  section: string;
  image_prompt?: string;
  midjourney_prompt?: string;
  alt_text: string;
  status: string;
  original_url?: string;
  hosted_url?: string;
  error?: string;
  approved?: boolean | null;
}

interface Props {
  taskId: string;
  images: ImageData[];
  paused: boolean;
  onRefresh: () => void;
}

export default function ImageReviewPanel({ taskId, images, paused, onRefresh }: Props) {
  const queryClient = useQueryClient();
  const [selections, setSelections] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    images.forEach((img) => {
      if (img.status === "completed") init[img.id] = img.approved !== false;
    });
    return init;
  });
  const [expandedPrompt, setExpandedPrompt] = useState<string | null>(null);
  const [regenPrompt, setRegenPrompt] = useState<Record<string, string>>({});

  const approveMutation = useMutation({
    mutationFn: () => {
      const approved = Object.entries(selections).filter(([, v]) => v).map(([k]) => k);
      const skipped = Object.entries(selections).filter(([, v]) => !v).map(([k]) => k);
      return tasksApi.approveImages(taskId, approved, skipped);
    },
    onSuccess: (data) => {
      toast.success(data.msg);
      queryClient.invalidateQueries({ queryKey: ["task", taskId] });
      queryClient.invalidateQueries({ queryKey: ["task-steps", taskId] });
      queryClient.invalidateQueries({ queryKey: ["task-images", taskId] });
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail || "Failed to approve"),
  });

  const regenMutation = useMutation({
    mutationFn: ({ imageId, newPrompt }: { imageId: string; newPrompt: string }) =>
      tasksApi.regenerateImage(taskId, imageId, newPrompt),
    onSuccess: () => {
      toast.success("Image regenerated!");
      onRefresh();
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail || "Regeneration failed"),
  });

  const completedImages = images.filter((i) => i.status === "completed");
  const failedImages = images.filter((i) => i.status === "failed");

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="flex items-center justify-between bg-slate-50 px-4 py-3 rounded border text-sm">
        <span className="text-slate-600">
          <span className="font-medium text-emerald-700">{completedImages.length}</span> generated
          {failedImages.length > 0 && (
            <> · <span className="font-medium text-red-600">{failedImages.length}</span> failed</>
          )}
        </span>
        {paused && (
          <span className="text-purple-600 font-medium text-xs">🖼️ Pipeline paused — review images below</span>
        )}
      </div>

      {/* Image cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {images.map((img) => (
          <div
            key={img.id}
            className={`rounded-lg border overflow-hidden transition-all ${
              img.status === "failed"
                ? "border-red-200 bg-red-50"
                : selections[img.id]
                ? "border-emerald-300 bg-emerald-50/30 ring-2 ring-emerald-200"
                : "border-slate-200 bg-white"
            }`}
          >
            {/* Image preview */}
            {img.hosted_url ? (
              <div className="relative group">
                <img
                  src={img.hosted_url}
                  alt={img.alt_text}
                  className="w-full h-48 object-cover"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />
              </div>
            ) : (
              <div className="h-48 flex items-center justify-center bg-slate-100 text-slate-400 text-sm">
                {img.status === "failed" ? `❌ ${img.error || "Failed"}` : "No image available"}
              </div>
            )}

            {/* Card body */}
            <div className="p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-slate-500">{img.id}</span>
                <span className="text-xs rounded bg-slate-100 px-2 py-0.5 text-slate-600">{img.section}</span>
              </div>

              <p className="text-xs text-slate-600 line-clamp-2">{img.alt_text}</p>

              {/* Prompt toggle */}
              <button
                onClick={() => setExpandedPrompt(expandedPrompt === img.id ? null : img.id)}
                className="text-xs text-blue-600 hover:underline flex items-center gap-1"
              >
                {expandedPrompt === img.id ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                {expandedPrompt === img.id ? "Hide prompt" : "Show prompt"}
              </button>

              {expandedPrompt === img.id && (
                <div className="bg-slate-900 rounded p-2 text-xs text-emerald-400 font-mono max-h-24 overflow-auto">
                  {img.image_prompt || img.midjourney_prompt || ""}
                </div>
              )}

              {/* Actions */}
              {paused && img.status === "completed" && (
                <div className="flex items-center gap-2 pt-1">
                  <button
                    onClick={() => setSelections((s) => ({ ...s, [img.id]: !s[img.id] }))}
                    className={`flex-1 text-xs py-1.5 rounded font-medium transition-colors ${
                      selections[img.id]
                        ? "bg-emerald-600 text-white"
                        : "bg-slate-200 text-slate-600 hover:bg-slate-300"
                    }`}
                  >
                    {selections[img.id] ? (
                      <><Check className="w-3 h-3 inline mr-1" />Approved</>
                    ) : (
                      <><X className="w-3 h-3 inline mr-1" />Skipped</>
                    )}
                  </button>
                  <button
                    onClick={() =>
                      regenMutation.mutate({ imageId: img.id, newPrompt: regenPrompt[img.id] || "" })
                    }
                    disabled={regenMutation.isPending}
                    className="px-2 py-1.5 text-xs rounded border border-slate-300 text-slate-600 hover:bg-slate-100 disabled:opacity-40"
                    title="Regenerate"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${regenMutation.isPending ? "animate-spin" : ""}`} />
                  </button>
                </div>
              )}

              {paused && img.status === "failed" && (
                <div className="flex gap-1 pt-1">
                  <input
                    type="text"
                    placeholder="New prompt (optional)..."
                    value={regenPrompt[img.id] || ""}
                    onChange={(e) => setRegenPrompt((p) => ({ ...p, [img.id]: e.target.value }))}
                    className="flex-1 text-xs border rounded px-2 py-1"
                  />
                  <button
                    onClick={() =>
                      regenMutation.mutate({ imageId: img.id, newPrompt: regenPrompt[img.id] || "" })
                    }
                    disabled={regenMutation.isPending}
                    className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-40"
                  >
                    Retry
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Approve all button */}
      {paused && (
        <div className="flex items-center justify-between px-4 py-4 border-t bg-slate-50 rounded-b-lg">
          <span className="text-sm text-slate-500">
            <span className="font-mono font-medium text-slate-700">
              {Object.values(selections).filter(Boolean).length}
            </span>{" "}
            images approved
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
                Submitting…
              </>
            ) : (
              <>✅ Confirm & Resume Pipeline</>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
