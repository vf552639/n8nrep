import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import api from "@/api/client";
import type { PromptPreset, PromptPresetCreate } from "@/types/promptPreset";

interface PromptListItem {
  id: string;
  agent_name: string;
  model: string;
  version: number;
}

interface Props {
  initial?: PromptPreset | null;
  onSubmit: (body: PromptPresetCreate) => Promise<void>;
  onCancel: () => void;
  busy: boolean;
}

export default function PromptPresetEditor({ initial, onSubmit, onCancel, busy }: Props) {
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [isDefault, setIsDefault] = useState(initial?.is_default ?? false);
  const [items, setItems] = useState<{ agent_name: string; prompt_id: string }[]>(
    initial?.items.map((i) => ({ agent_name: i.agent_name, prompt_id: i.prompt_id })) ?? [],
  );

  useEffect(() => {
    if (initial) {
      setName(initial.name);
      setDescription(initial.description ?? "");
      setIsDefault(initial.is_default);
      setItems(initial.items.map((i) => ({ agent_name: i.agent_name, prompt_id: i.prompt_id })));
    }
  }, [initial]);

  const { data: prompts = [] } = useQuery({
    queryKey: ["prompts", "all"],
    queryFn: () => api.get<PromptListItem[]>("/prompts?active_only=false").then((r) => r.data),
  });

  const agents = useMemo(
    () => Array.from(new Set(prompts.map((p) => p.agent_name))).sort(),
    [prompts],
  );

  function addItem() {
    if (agents.length === 0) return;
    const first = prompts.find((p) => p.agent_name === agents[0]);
    if (!first) return;
    setItems((prev) => [...prev, { agent_name: agents[0], prompt_id: first.id }]);
  }

  function updateItem(idx: number, patch: Partial<{ agent_name: string; prompt_id: string }>) {
    setItems((prev) => prev.map((it, i) => (i === idx ? { ...it, ...patch } : it)));
  }

  function removeItem(idx: number) {
    setItems((prev) => prev.filter((_, i) => i !== idx));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await onSubmit({ name, description, is_default: isDefault, items });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 border rounded-lg p-4 bg-white">
      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1 text-xs">
          <span className="font-medium text-slate-700">Name</span>
          <input
            className="border rounded px-2 py-1"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </label>
        <label className="flex items-center gap-2 text-xs mt-5">
          <input
            type="checkbox"
            checked={isDefault}
            onChange={(e) => setIsDefault(e.target.checked)}
          />
          Default preset
        </label>
      </div>
      <label className="flex flex-col gap-1 text-xs">
        <span className="font-medium text-slate-700">Description</span>
        <textarea
          className="border rounded px-2 py-1 min-h-[60px]"
          value={description ?? ""}
          onChange={(e) => setDescription(e.target.value)}
        />
      </label>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Agent → prompt overrides</span>
          <button
            type="button"
            className="text-xs flex items-center gap-1 text-blue-600"
            onClick={addItem}
          >
            <Plus className="w-3 h-3" /> Add agent
          </button>
        </div>
        {items.length === 0 && (
          <div className="text-xs text-slate-500">
            No overrides — falls back to active prompts.
          </div>
        )}
        {items.map((it, idx) => {
          const promptsForAgent = prompts.filter((p) => p.agent_name === it.agent_name);
          return (
            <div key={idx} className="flex gap-2 items-end">
              <select
                className="border rounded px-2 py-1 text-sm flex-1"
                value={it.agent_name}
                onChange={(e) => {
                  const agent = e.target.value;
                  const first = prompts.find((p) => p.agent_name === agent);
                  updateItem(idx, { agent_name: agent, prompt_id: first?.id ?? "" });
                }}
              >
                {agents.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </select>
              <select
                className="border rounded px-2 py-1 text-sm flex-1"
                value={it.prompt_id}
                onChange={(e) => updateItem(idx, { prompt_id: e.target.value })}
              >
                {promptsForAgent.map((p) => (
                  <option key={p.id} value={p.id}>{`v${p.version} — ${p.model}`}</option>
                ))}
              </select>
              <button
                type="button"
                className="text-red-600"
                onClick={() => removeItem(idx)}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          );
        })}
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <button
          type="button"
          className="px-3 py-1.5 text-sm rounded border"
          onClick={onCancel}
          disabled={busy}
        >
          Cancel
        </button>
        <button
          type="submit"
          className="px-3 py-1.5 text-sm rounded bg-blue-600 text-white"
          disabled={busy}
        >
          {initial ? "Save" : "Create"}
        </button>
      </div>
    </form>
  );
}
