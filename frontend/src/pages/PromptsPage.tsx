import { useState, useEffect, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Editor from "@monaco-editor/react";
import toast from "react-hot-toast";
import api from "@/api/client";
import { promptsApi } from "@/api/prompts";
import { Prompt } from "@/types/prompt";
import { ModelSelector } from "@/components/ModelSelector";
import CopyButton from "@/components/common/CopyButton";
import {
  Play,
  Save,
  X,
  FileJson,
  Loader2,
  Search,
  PanelRightOpen,
  Copy,
} from "lucide-react";

const AGENT_MAP: Record<string, string> = {
  ai_structure_analysis: "AI Structure Analysis",
  chunk_cluster_analysis: "Chunk Cluster Analysis",
  competitor_structure_analysis: "Competitor Structure",
  final_structure_analysis: "Final Structure Analysis",
  structure_fact_checking: "Structure Fact-Checking",
  image_prompt_generation: "Image Prompts (LLM)",
  image_generation: "Image Creation (OpenRouter)",
  primary_generation: "Primary Generation",
  competitor_comparison: "Competitor Comparison",
  reader_opinion: "Reader Opinion",
  interlinking_citations: "Interlinking & Citations",
  improver: "Improver",
  final_editing: "Final Editing",
  content_fact_checking: "Content Fact-Checking",
  html_structure: "HTML Structure",
  meta_generation: "Meta Generation",
};

/** Same order as pipeline LLM agents in StepMonitor (ALL_STEPS minus serp + scraping). */
const AGENT_ORDER = [
  "ai_structure_analysis",
  "chunk_cluster_analysis",
  "competitor_structure_analysis",
  "final_structure_analysis",
  "structure_fact_checking",
  "image_prompt_generation",
  "image_generation",
  "primary_generation",
  "competitor_comparison",
  "reader_opinion",
  "interlinking_citations",
  "improver",
  "final_editing",
  "content_fact_checking",
  "html_structure",
  "meta_generation",
] as const;

const PROMPT_VARIABLES = [
  {
    group: "Task & Project",
    vars: [
      { name: "keyword", desc: "Главное ключевое слово" },
      { name: "additional_keywords", desc: "Доп. ключевые слова (LSI)" },
      { name: "country", desc: "Страна" },
      { name: "language", desc: "Язык" },
      { name: "page_type", desc: "Тип страницы (homepage, category, article)" },
      { name: "site_name", desc: "Название целевого сайта" },
      { name: "site_template_html", desc: "HTML-шаблон целевого сайта" },
      { name: "site_template_name", desc: "Название шаблона сайта" },
    ],
  },
  {
    group: "Author & Style",
    vars: [
      { name: "author", desc: "Имя автора" },
      { name: "author_style", desc: "Биография / описание автора" },
      { name: "imitation", desc: "Подражание (Mimicry)" },
      { name: "target_audience", desc: "Целевая аудитория" },
      { name: "face", desc: "Лицо повествования (POV)" },
      { name: "year", desc: "Год" },
      { name: "rhythms_style", desc: "Ритм и стиль" },
      { name: "exclude_words", desc: "Слова-исключения (глобальные)" },
    ],
  },
  {
    group: "Competitors & SERP",
    vars: [
      { name: "competitors_headers", desc: "Структура h1-h6 конкурентов (JSON)" },
      { name: "merged_markdown", desc: "Объединённый текст конкурентов" },
      { name: "avg_word_count", desc: "Среднее кол-во слов у конкурентов" },
      { name: "competitor_titles", desc: "Titles конкурентов из SERP (JSON)" },
      { name: "competitor_descriptions", desc: "Descriptions конкурентов (JSON)" },
      { name: "highlighted_keywords", desc: "Выделенные слова в сниппетах (JSON)" },
      { name: "paa_with_answers", desc: "People Also Ask с ответами" },
      { name: "featured_snippet", desc: "Featured Snippet (JSON)" },
      { name: "knowledge_graph", desc: "Knowledge Graph (JSON)" },
      { name: "ai_overview", desc: "Google AI Overview текст" },
      { name: "answer_box", desc: "Answer Box текст" },
      { name: "serp_features", desc: "SERP-элементы на странице (JSON)" },
      { name: "search_intent_signals", desc: "Сигналы поискового интента (JSON)" },
      { name: "related_searches", desc: "Related Searches от Google (JSON)" },
    ],
  },
  {
    group: "Pipeline Results",
    vars: [
      { name: "result_ai_structure_analysis", desc: "AI анализ структуры" },
      { name: "intent", desc: "└ Поисковый интент" },
      { name: "Taxonomy", desc: "└ Таксономия запроса" },
      { name: "Attention", desc: "└ На что обратить внимание" },
      { name: "structura", desc: "└ Рекомендованная структура" },
      { name: "result_chunk_cluster_analysis", desc: "Анализ кластера (Чанки)" },
      { name: "result_competitor_structure_analysis", desc: "Анализ конкурентов" },
      { name: "result_final_structure_analysis", desc: "Финальный анализ структуры (JSON)" },
      { name: "structure_fact_checking", desc: "Фактический анализ структуры (Отчет)" },
      { name: "result_image_prompt_generation", desc: "Промпты для картинок (JSON)" },
      { name: "result_image_generation", desc: "Сгенерированные картинки (JSON)" },
      { name: "result_primary_generation", desc: "Первичная генерация (HTML)" },
      { name: "result_competitor_comparison", desc: "Сравнение с конкурентами" },
      { name: "result_reader_opinion", desc: "Мнение читателя" },
      { name: "result_interlinking_citations", desc: "Перелинковка и цитаты" },
      { name: "result_improver", desc: "Улучшайзер" },
      { name: "result_final_editing", desc: "Финальная редактура" },
      { name: "result_html_structure", desc: "Структура HTML" },
      { name: "result_meta_generation", desc: "Генерация мета-тегов" },
    ],
  },
];

const VAR_COUNT = PROMPT_VARIABLES.reduce((acc, g) => acc + g.vars.length, 0);

const DEFAULT_TEST_JSON = `{
  "keyword": "SEO Strategy 2024",
  "language": "en",
  "country": "us"
}`;

function normalizePrompt(p: Partial<Prompt> | null) {
  if (!p) return null;
  return {
    system_prompt: p.system_prompt ?? "",
    user_prompt: p.user_prompt ?? "",
    model: p.model ?? "",
    max_tokens: p.max_tokens ?? null,
    temperature: p.temperature ?? 0.7,
    frequency_penalty: p.frequency_penalty ?? 0,
    presence_penalty: p.presence_penalty ?? 0,
    top_p: p.top_p ?? 1,
    skip_in_pipeline: !!p.skip_in_pipeline,
  };
}

function isPromptDirty(
  edit: Partial<Prompt> | null,
  saved: Prompt | null | undefined,
  params: { maxTokens: boolean; temp: boolean; freq: boolean; pres: boolean; top: boolean }
) {
  if (!edit || !saved) return false;
  const e = normalizePrompt(edit);
  const s = normalizePrompt(saved);
  if (!e || !s) return false;
  if (e.system_prompt !== s.system_prompt || e.user_prompt !== s.user_prompt) return true;
  if (e.model !== s.model) return true;
  if (e.skip_in_pipeline !== s.skip_in_pipeline) return true;

  const savMaxOn = s.max_tokens != null && s.max_tokens > 0;
  if (params.maxTokens !== savMaxOn) return true;
  if (params.maxTokens && (e.max_tokens ?? null) !== (s.max_tokens ?? null)) return true;

  const savTempOn = (saved.temperature ?? 0.7) !== 1.0;
  if (params.temp !== savTempOn) return true;
  const effTemp = params.temp ? e.temperature : 1.0;
  if (effTemp !== (saved.temperature ?? 0.7)) return true;

  const savFreq = (saved.frequency_penalty ?? 0) !== 0.0;
  const savPres = (saved.presence_penalty ?? 0) !== 0.0;
  const savTop = (saved.top_p ?? 1) !== 1.0;
  if (params.freq !== savFreq || params.pres !== savPres || params.top !== savTop) return true;
  const effFreq = params.freq ? e.frequency_penalty : 0;
  const effPres = params.pres ? e.presence_penalty : 0;
  const effTop = params.top ? e.top_p : 1;
  if (effFreq !== (saved.frequency_penalty ?? 0)) return true;
  if (effPres !== (saved.presence_penalty ?? 0)) return true;
  if (effTop !== (saved.top_p ?? 1)) return true;
  return false;
}

type TestTab = "context" | "result" | "resolved";

interface TestResultShape {
  output?: string;
  cost?: number;
  model_used?: string;
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
    cost?: number;
  };
  resolved_prompts?: { system_prompt: string; user_prompt: string };
  error?: string;
}

export default function PromptsPage() {
  const queryClient = useQueryClient();
  const [activePromptId, setActivePromptId] = useState<string | null>(null);
  const [editState, setEditState] = useState<Partial<Prompt> | null>(null);
  const [isTestOpen, setIsTestOpen] = useState(false);
  const [testTab, setTestTab] = useState<TestTab>("context");
  const [variablesQuery, setVariablesQuery] = useState("");
  const [paramsEnabled, setParamsEnabled] = useState({
    maxTokens: false,
    temp: false,
    freq: false,
    pres: false,
    top: false,
  });
  const [variablesDrawerOpen, setVariablesDrawerOpen] = useState(false);


  const { data: prompts, isLoading } = useQuery({
    queryKey: ["prompts"],
    queryFn: () => promptsApi.getAll(),
  });

  const filteredPrompts = useMemo(() => {
    if (!prompts) return undefined;
    const orderSet = new Set<string>(AGENT_ORDER);
    const byAgent = new Map(
      prompts
        .filter((p: Prompt) => orderSet.has(p.agent_name))
        .map((p: Prompt) => [p.agent_name, p])
    );
    return AGENT_ORDER.map((name) => byAgent.get(name)).filter(Boolean) as Prompt[];
  }, [prompts]);
  const activePromptListInfo = filteredPrompts?.find((p) => p.id === activePromptId) || filteredPrompts?.[0];
  const derivedActiveId = activePromptId || activePromptListInfo?.id;

  const { data: orModels } = useQuery({
    queryKey: ["openrouter-models"],
    queryFn: async () => {
      const res = await api.get("/settings/openrouter-models");
      return res.data.models as string[];
    },
    staleTime: 3600000,
  });

  const { data: fullPrompt, isLoading: isLoadingPrompt } = useQuery({
    queryKey: ["prompt", derivedActiveId],
    queryFn: () => (derivedActiveId ? promptsApi.getOne(derivedActiveId) : null),
    enabled: !!derivedActiveId,
  });



  useEffect(() => {
    if (!activePromptId && derivedActiveId) {
      setActivePromptId(derivedActiveId);
    }
  }, [activePromptId, derivedActiveId]);

  useEffect(() => {
    if (!fullPrompt) return;
    if (fullPrompt.id !== editState?.id) {
      const cleanPrompt = { ...fullPrompt };
      if (cleanPrompt.temperature !== undefined) cleanPrompt.temperature = Math.round(cleanPrompt.temperature * 10) / 10;
      if (cleanPrompt.frequency_penalty !== undefined) cleanPrompt.frequency_penalty = Math.round(cleanPrompt.frequency_penalty * 10) / 10;
      if (cleanPrompt.presence_penalty !== undefined) cleanPrompt.presence_penalty = Math.round(cleanPrompt.presence_penalty * 10) / 10;
      if (cleanPrompt.top_p !== undefined) cleanPrompt.top_p = Math.round(cleanPrompt.top_p * 10) / 10;

      setEditState(cleanPrompt);
      setParamsEnabled({
        maxTokens: cleanPrompt.max_tokens != null && cleanPrompt.max_tokens > 0,
        temp: (cleanPrompt.temperature ?? 0.7) !== 1.0,
        freq: (cleanPrompt.frequency_penalty ?? 0) !== 0.0,
        pres: (cleanPrompt.presence_penalty ?? 0) !== 0.0,
        top: (cleanPrompt.top_p ?? 1) !== 1.0,
      });
    }
  }, [fullPrompt, editState?.id]);

  const isDirty = useMemo(
    () => isPromptDirty(editState, fullPrompt ?? null, paramsEnabled),
    [editState, fullPrompt, paramsEnabled]
  );



  const saveMutation = useMutation({
    mutationFn: (data: Partial<Prompt>) => {
      const payload: Partial<Prompt> = {
        ...data,
        max_tokens: paramsEnabled.maxTokens ? (data.max_tokens ?? null) : null,
        temperature: paramsEnabled.temp ? (data.temperature ?? 0.7) : 1.0,
        frequency_penalty: paramsEnabled.freq ? (data.frequency_penalty ?? 0.0) : 0.0,
        presence_penalty: paramsEnabled.pres ? (data.presence_penalty ?? 0.0) : 0.0,
        top_p: paramsEnabled.top ? (data.top_p ?? 1.0) : 1.0,
      };
      return promptsApi.update(payload);
    },
    onSuccess: (data) => {
      toast.success("Prompt saved successfully");
      setActivePromptId(data.id);
      setEditState(null);
      queryClient.invalidateQueries({ queryKey: ["prompts"] });
      queryClient.invalidateQueries({ queryKey: ["prompt", data.id] });
      queryClient.invalidateQueries({ queryKey: ["prompt-versions", data.id] });
    },
    onError: () => toast.error("Failed to save prompt"),
  });



  const requestSelectAgent = (nextId: string) => {
    if (nextId === activePromptId) return;
    if (isDirty) {
      if (!window.confirm("You have unsaved changes. Switch agent and discard edits?")) return;
    }
    setActivePromptId(nextId);
    setIsTestOpen(false);
  };

  const copyVar = (name: string) => {
    navigator.clipboard.writeText(`{{${name}}}`);
    toast.success(`Copied {{${name}}}`);
  };

  const variableExplorerInner = (
    <>
      <div className="border-b p-2">
        <div className="relative">
          <Search className="absolute left-2 top-1.5 h-3.5 w-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search..."
            value={variablesQuery}
            onChange={(e) => setVariablesQuery(e.target.value)}
            className="w-full rounded border border-slate-200 bg-white py-1 pl-7 pr-2 text-[11px] shadow-sm focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
          />
          {variablesQuery && (
            <button
              type="button"
              onClick={() => setVariablesQuery("")}
              className="absolute right-1.5 top-1.5 text-slate-400 hover:text-slate-600"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-auto p-2">
        {PROMPT_VARIABLES.map((group) => {
          const filteredVars = group.vars.filter(
            (v) =>
              v.name.toLowerCase().includes(variablesQuery.toLowerCase()) ||
              v.desc.toLowerCase().includes(variablesQuery.toLowerCase())
          );

          if (filteredVars.length === 0) return null;

          return (
            <div key={group.group} className="space-y-1">
              <h4 className="border-b border-slate-100 pb-0.5 text-[9px] font-bold uppercase tracking-wider text-slate-500">
                {group.group}
              </h4>
              <div className="space-y-0.5">
                {filteredVars.map((v) => (
                  <button
                    key={v.name}
                    type="button"
                    draggable
                    title={v.desc}
                    onDragStart={(e) => {
                      e.dataTransfer.setData("text/plain", `{{${v.name}}}`);
                      e.dataTransfer.effectAllowed = "copy";
                    }}
                    onClick={() => copyVar(v.name)}
                    className="flex w-full items-center justify-between gap-2 rounded border border-slate-200 bg-slate-50 px-2 py-1 text-left font-mono text-[11px] text-teal-700 hover:bg-slate-100"
                  >
                    <span className="min-w-0 flex-1 truncate">{`{{${v.name}}}`}</span>
                    <Copy className="h-3.5 w-3.5 shrink-0 text-slate-400" aria-hidden />
                  </button>
                ))}
              </div>
            </div>
          );
        })}

        {PROMPT_VARIABLES.every(
          (g) =>
            g.vars.filter(
              (v) =>
                v.name.toLowerCase().includes(variablesQuery.toLowerCase()) ||
                v.desc.toLowerCase().includes(variablesQuery.toLowerCase())
            ).length === 0
        ) && <div className="py-3 text-center text-[11px] text-slate-500">No variables found</div>}
      </div>
    </>
  );

  const attachVarDrop = (editor: { getDomNode: () => HTMLElement | null; trigger: (s: string, t: string, a: { text: string }) => void; onDidDispose: (fn: () => void) => void }) => {
    const el = editor.getDomNode();
    if (!el) return;
    const onOver = (e: DragEvent) => {
      e.preventDefault();
      try {
        if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
      } catch {
        /* ignore */
      }
    };
    const onDrop = (e: DragEvent) => {
      e.preventDefault();
      const t = e.dataTransfer?.getData("text/plain");
      if (t) editor.trigger("keyboard", "type", { text: t });
    };
    el.addEventListener("dragover", onOver);
    el.addEventListener("drop", onDrop);
    editor.onDidDispose(() => {
      el.removeEventListener("dragover", onOver);
      el.removeEventListener("drop", onDrop);
    });
  };

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 px-3">
      <h1 className="shrink-0 text-xl font-bold text-slate-900">SEO Workflow Optimizer</h1>

      {activePromptListInfo && editState && !isLoadingPrompt && (
        <div className="w-full min-w-0 shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-2.5 shadow-sm">
          <div className="flex flex-wrap items-end gap-x-3 gap-y-2">
            <div className="w-[280px] shrink-0 min-w-0">
              <span className="mb-0.5 block text-xs font-medium text-slate-600">Model</span>
              <ModelSelector
                className="w-full min-w-0"
                value={editState.model || "openai/gpt-4o"}
                models={orModels || ["openai/gpt-4o"]}
                onChange={(m) => setEditState((prev) => (prev ? { ...prev, model: m } : null))}
              />
            </div>

            <div className="w-[160px] shrink-0">
              <span className="mb-0.5 block text-xs font-medium text-slate-600">Max tokens</span>
              <label className="flex items-center gap-1.5 text-xs text-slate-700">
                <input
                  type="checkbox"
                  className="rounded border-slate-300 text-blue-600"
                  checked={paramsEnabled.maxTokens}
                  onChange={(e) => {
                    const checked = e.target.checked;
                    setParamsEnabled((p) => ({ ...p, maxTokens: checked }));
                    if (!checked) {
                      setEditState((prev) => (prev ? { ...prev, max_tokens: null } : null));
                    } else {
                      setEditState((prev) => {
                        if (!prev) return null;
                        const fromPrev =
                          prev.max_tokens != null && prev.max_tokens > 0 ? prev.max_tokens : null;
                        const fromDb =
                          fullPrompt && fullPrompt.max_tokens != null && fullPrompt.max_tokens > 0
                            ? fullPrompt.max_tokens
                            : null;
                        return { ...prev, max_tokens: fromPrev ?? fromDb ?? 4000 };
                      });
                    }
                  }}
                />
                <input
                  type="number"
                  min={1}
                  max={200000}
                  step={1}
                  placeholder="default"
                  disabled={!paramsEnabled.maxTokens}
                  value={paramsEnabled.maxTokens ? (editState.max_tokens ?? "") : ""}
                  onChange={(e) => {
                    const raw = e.target.value;
                    setEditState((prev) =>
                      prev
                        ? {
                            ...prev,
                            max_tokens: raw === "" ? null : parseInt(raw, 10) || null,
                          }
                        : null
                    );
                  }}
                  className="min-w-0 flex-1 rounded border border-slate-200 bg-white px-1.5 py-0.5 text-right font-mono text-xs disabled:cursor-not-allowed disabled:opacity-40"
                />
              </label>
            </div>

            <div className="w-[180px] shrink-0">
              <span className="mb-0.5 block text-xs font-medium text-slate-600">Temperature</span>
              <div className="flex flex-col gap-1">
                <label className="flex items-center gap-1.5 text-xs text-slate-700">
                  <input
                    type="checkbox"
                    className="rounded border-slate-300 text-blue-600"
                    checked={paramsEnabled.temp}
                    onChange={(e) => {
                      const checked = e.target.checked;
                      setParamsEnabled((p) => ({ ...p, temp: checked }));
                      if (!checked) setEditState((prev) => (prev ? { ...prev, temperature: 1.0 } : null));
                    }}
                  />
                  <span className="whitespace-nowrap">Custom</span>
                </label>
                <div className="flex min-w-0 items-center gap-1">
                  <input
                    type="range"
                    min={0}
                    max={2}
                    step={0.1}
                    disabled={!paramsEnabled.temp}
                    value={editState.temperature ?? 0.7}
                    onChange={(e) =>
                      setEditState((prev) => (prev ? { ...prev, temperature: parseFloat(e.target.value) } : null))
                    }
                    className="h-1 min-w-0 flex-1 cursor-pointer accent-blue-600 disabled:cursor-not-allowed disabled:opacity-40"
                  />
                  <input
                    type="number"
                    step={0.1}
                    min={0}
                    max={2}
                    disabled={!paramsEnabled.temp}
                    value={editState.temperature ?? 0.7}
                    onChange={(e) =>
                      setEditState((prev) => (prev ? { ...prev, temperature: parseFloat(e.target.value) } : null))
                    }
                    onBlur={(e) => {
                      const val = Math.min(Math.max(Math.round(parseFloat(e.target.value) * 10) / 10, 0), 2);
                      setEditState((prev) => (prev ? { ...prev, temperature: val } : null));
                    }}
                    className="w-14 shrink-0 rounded border border-slate-200 bg-white px-1 py-0.5 text-right font-mono text-xs disabled:opacity-40"
                  />
                </div>
              </div>
            </div>

            <div className="w-[160px] shrink-0">
              <span className="mb-0.5 block text-xs font-medium text-slate-600">Freq. Penalty</span>
              <label className="flex items-center gap-1.5 text-xs text-slate-700">
                <input
                  type="checkbox"
                  className="rounded border-slate-300 text-blue-600"
                  checked={paramsEnabled.freq}
                  onChange={(e) => {
                    const checked = e.target.checked;
                    setParamsEnabled((p) => ({ ...p, freq: checked }));
                    if (!checked) setEditState((prev) => (prev ? { ...prev, frequency_penalty: 0.0 } : null));
                  }}
                />
                <input
                  type="number"
                  step={0.1}
                  min={-2}
                  max={2}
                  disabled={!paramsEnabled.freq}
                  value={editState.frequency_penalty ?? 0.0}
                  onChange={(e) =>
                    setEditState((prev) => (prev ? { ...prev, frequency_penalty: parseFloat(e.target.value) } : null))
                  }
                  onBlur={(e) => {
                    const val = Math.min(Math.max(Math.round(parseFloat(e.target.value) * 10) / 10, -2), 2);
                    setEditState((prev) => (prev ? { ...prev, frequency_penalty: val } : null));
                  }}
                  className="min-w-0 flex-1 rounded border border-slate-200 bg-white px-1.5 py-0.5 text-right font-mono text-xs disabled:opacity-40"
                />
              </label>
            </div>

            <div className="w-[160px] shrink-0">
              <span className="mb-0.5 block text-xs font-medium text-slate-600">Pres. Penalty</span>
              <label className="flex items-center gap-1.5 text-xs text-slate-700">
                <input
                  type="checkbox"
                  className="rounded border-slate-300 text-blue-600"
                  checked={paramsEnabled.pres}
                  onChange={(e) => {
                    const checked = e.target.checked;
                    setParamsEnabled((p) => ({ ...p, pres: checked }));
                    if (!checked) setEditState((prev) => (prev ? { ...prev, presence_penalty: 0.0 } : null));
                  }}
                />
                <input
                  type="number"
                  step={0.1}
                  min={-2}
                  max={2}
                  disabled={!paramsEnabled.pres}
                  value={editState.presence_penalty ?? 0.0}
                  onChange={(e) =>
                    setEditState((prev) => (prev ? { ...prev, presence_penalty: parseFloat(e.target.value) } : null))
                  }
                  onBlur={(e) => {
                    const val = Math.min(Math.max(Math.round(parseFloat(e.target.value) * 10) / 10, -2), 2);
                    setEditState((prev) => (prev ? { ...prev, presence_penalty: val } : null));
                  }}
                  className="min-w-0 flex-1 rounded border border-slate-200 bg-white px-1.5 py-0.5 text-right font-mono text-xs disabled:opacity-40"
                />
              </label>
            </div>

            <div className="w-[140px] shrink-0">
              <span className="mb-0.5 block text-xs font-medium text-slate-600">Top P</span>
              <label className="flex items-center gap-1.5 text-xs text-slate-700">
                <input
                  type="checkbox"
                  className="rounded border-slate-300 text-blue-600"
                  checked={paramsEnabled.top}
                  onChange={(e) => {
                    const checked = e.target.checked;
                    setParamsEnabled((p) => ({ ...p, top: checked }));
                    if (!checked) setEditState((prev) => (prev ? { ...prev, top_p: 1.0 } : null));
                  }}
                />
                <input
                  type="number"
                  step={0.1}
                  min={0}
                  max={1}
                  disabled={!paramsEnabled.top}
                  value={editState.top_p ?? 1.0}
                  onChange={(e) => setEditState((prev) => (prev ? { ...prev, top_p: parseFloat(e.target.value) } : null))}
                  onBlur={(e) => {
                    const val = Math.min(Math.max(Math.round(parseFloat(e.target.value) * 10) / 10, 0), 1);
                    setEditState((prev) => (prev ? { ...prev, top_p: val } : null));
                  }}
                  className="min-w-0 flex-1 rounded border border-slate-200 bg-white px-1.5 py-0.5 text-right font-mono text-xs disabled:opacity-40"
                />
              </label>
            </div>

            <div className="ml-auto flex shrink-0 items-center gap-2">
              <button
                type="button"
                onClick={() => saveMutation.mutate(editState)}
                disabled={saveMutation.isPending || !isDirty}
                className="relative inline-flex items-center gap-1.5 rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-emerald-700 disabled:opacity-70"
              >
                {isDirty && (
                  <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-amber-300 ring-2 ring-white" aria-hidden />
                )}
                <Save className="h-4 w-4" />
                {isDirty ? "Save*" : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex min-h-0 min-w-0 flex-1 gap-2 xl:gap-3">
        <div className="flex w-[240px] shrink-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm min-h-0">
          <div className="shrink-0 border-b border-slate-200 bg-slate-50 px-3 py-3 text-sm font-semibold text-slate-800">
            Available Agents
          </div>
          <div className="min-h-0 flex-1 space-y-0.5 overflow-auto p-2">
            {isLoading ? (
              <div className="p-4 text-center text-sm text-slate-500">Loading prompts...</div>
            ) : (
              filteredPrompts?.map((prompt: Prompt) => {
                const selected = activePromptId
                  ? activePromptId === prompt.id
                  : filteredPrompts?.[0]?.id === prompt.id;
                const skipped = prompt.skip_in_pipeline;
                const dotClass = selected ? "bg-blue-500" : skipped ? "bg-slate-400" : "bg-emerald-500";
                return (
                  <button
                    key={prompt.id}
                    type="button"
                    onClick={() => requestSelectAgent(prompt.id)}
                    className={`flex w-full items-start gap-2 rounded-md border-l-2 py-2 pl-2 pr-2 text-left text-sm transition-colors ${
                      selected
                        ? "border-blue-500 bg-blue-50 font-medium text-blue-800"
                        : "border-transparent text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${dotClass}`} aria-hidden />
                    <span className={`min-w-0 flex-1 ${skipped ? "text-slate-500 line-through" : ""}`}>
                      {AGENT_MAP[prompt.agent_name] || prompt.agent_name.replace(/_/g, " ")}
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </div>

        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-none border border-slate-200 bg-white shadow-sm">
          {activePromptListInfo && editState && !isLoadingPrompt ? (
            <>
              <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-slate-200 bg-white px-3 py-2">
                <h2 className="min-w-0 flex-1 text-lg font-semibold capitalize text-slate-800 truncate">
                  {AGENT_MAP[activePromptListInfo.agent_name] || activePromptListInfo.agent_name.replace(/_/g, " ")}
                </h2>

                <button
                  type="button"
                  onClick={() => setVariablesDrawerOpen(true)}
                  className="inline-flex shrink-0 items-center gap-2 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50 xl:hidden"
                >
                  <PanelRightOpen className="h-3.5 w-3.5" />
                  Variables ({VAR_COUNT})
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsTestOpen((o) => !o);
                    if (isTestOpen) setTestTab("context");
                  }}
                  className={`inline-flex shrink-0 items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium shadow-sm transition-colors ${
                    isTestOpen
                      ? "border-blue-400 bg-blue-50 text-blue-800"
                      : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <Play className="h-3.5 w-3.5" />
                  Test
                </button>
                <label className="ml-auto flex shrink-0 cursor-pointer items-center gap-2 text-xs font-medium text-slate-700">
                  <input
                    type="checkbox"
                    className="rounded border-orange-300 text-orange-500 focus:ring-orange-500"
                    checked={editState.skip_in_pipeline || false}
                    onChange={(e) => setEditState((prev) => (prev ? { ...prev, skip_in_pipeline: e.target.checked } : null))}
                  />
                  Skip in pipeline
                </label>
              </div>

              <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
                <div className="flex min-h-0 flex-1 flex-col divide-y divide-slate-200 overflow-hidden">
                  <div className="flex min-h-[45%] min-w-0 flex-1 flex-col">
                    <div className="shrink-0 border-b border-slate-200 bg-slate-50 px-2.5 py-2 text-xs font-semibold uppercase tracking-wide text-slate-600">
                      System Prompt
                    </div>
                    <div className="relative min-h-0 flex-1 bg-white">
                      <Editor
                        height="100%"
                        language="markdown"
                        theme="vs"
                        value={editState.system_prompt || ""}
                        onChange={(val) => setEditState((prev) => (prev ? { ...prev, system_prompt: val || "" } : null))}
                        onMount={(ed) => attachVarDrop(ed)}
                        options={{
                          minimap: { enabled: false },
                          wordWrap: "on",
                          padding: { top: 16 },
                          unusualLineTerminators: "off",
                        }}
                        className="rounded-none"
                      />
                    </div>
                  </div>
                  <div className="flex min-h-[45%] min-w-0 flex-1 flex-col">
                    <div className="shrink-0 border-b border-slate-200 bg-slate-50 px-2.5 py-2 text-xs font-semibold uppercase tracking-wide text-slate-600">
                      User Prompt
                    </div>
                    <div className="relative min-h-0 flex-1 bg-white">
                      <Editor
                        height="100%"
                        language="markdown"
                        theme="vs"
                        value={editState.user_prompt || ""}
                        onChange={(val) => setEditState((prev) => (prev ? { ...prev, user_prompt: val || "" } : null))}
                        onMount={(ed) => attachVarDrop(ed)}
                        options={{
                          minimap: { enabled: false },
                          wordWrap: "on",
                          padding: { top: 16 },
                          unusualLineTerminators: "off",
                        }}
                        className="rounded-none"
                      />
                    </div>
                  </div>
                </div>

                {isTestOpen && editState.id && (
                  <PromptTestPanel
                    promptId={editState.id}
                    model={editState.model || "openai/gpt-4o"}
                    maxTokens={paramsEnabled.maxTokens ? (editState.max_tokens ?? null) : null}
                    agentLabel={AGENT_MAP[activePromptListInfo.agent_name] || activePromptListInfo.agent_name}
                    testTab={testTab}
                    setTestTab={setTestTab}
                    onClose={() => setIsTestOpen(false)}
                  />
                )}
              </div>
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center text-slate-500">Select an agent to view and edit prompts</div>
          )}
        </div>

        <div className="hidden min-h-0 w-[280px] shrink-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm xl:flex">
          <div className="flex shrink-0 items-center justify-between gap-2 border-b border-slate-200 bg-slate-50 px-3 py-2.5 font-semibold text-slate-800">
            <span className="text-sm">Variable Explorer</span>
            <span className="text-xs font-medium text-slate-600">({VAR_COUNT})</span>
          </div>
          <div className="flex min-h-0 flex-1 flex-col">{variableExplorerInner}</div>
        </div>
      </div>

      {variablesDrawerOpen && (
        <div className="fixed inset-0 z-50 xl:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-slate-900/40"
            aria-label="Close variables"
            onClick={() => setVariablesDrawerOpen(false)}
          />
          <div className="absolute inset-y-0 right-0 flex w-[min(100vw,320px)] flex-col border-l border-slate-200 bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-3 py-2">
              <span className="text-sm font-semibold text-slate-800">
                Variable Explorer <span className="text-slate-600">({VAR_COUNT})</span>
              </span>
              <button
                type="button"
                onClick={() => setVariablesDrawerOpen(false)}
                className="rounded-md p-1 text-slate-500 hover:bg-slate-200"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="flex min-h-0 flex-1 flex-col overflow-hidden">{variableExplorerInner}</div>
          </div>
        </div>
      )}
    </div>
  );
}

function PromptTestPanel({
  promptId,
  model,
  maxTokens,
  agentLabel,
  testTab,
  setTestTab,
  onClose,
}: {
  promptId: string;
  model: string;
  maxTokens: number | null;
  agentLabel: string;
  testTab: TestTab;
  setTestTab: (t: TestTab) => void;
  onClose: () => void;
}) {
  const [testContext, setTestContext] = useState(DEFAULT_TEST_JSON);
  const [result, setResult] = useState<TestResultShape | null>(null);

  useEffect(() => {
    setTestContext(DEFAULT_TEST_JSON);
    setResult(null);
    setTestTab("context");
  }, [promptId, setTestTab]);

  const testMutation = useMutation({
    mutationFn: async () => {
      let parsedContext: Record<string, unknown> = {};
      try {
        parsedContext = JSON.parse(testContext) as Record<string, unknown>;
      } catch {
        throw new Error("Invalid JSON in Test Context");
      }

      return promptsApi.testPrompt(promptId, {
        context: parsedContext,
        model,
        max_tokens: maxTokens,
      }) as Promise<TestResultShape>;
    },
    onSuccess: (data) => {
      setResult(data);
      setTestTab("result");
    },
    onError: (err: Error) => {
      setResult({ error: err.message || "Test failed" });
      toast.error(err.message || "Test failed");
    },
  });

  const outputText =
    result?.error ||
    (typeof result?.output === "string"
      ? result.output
      : result?.output != null
        ? JSON.stringify(result.output, null, 2)
        : "");

  return (
    <div className="flex h-[min(40vh,320px)] min-h-[260px] shrink-0 flex-col border-t border-slate-200 bg-slate-50/80">
      <div className="flex items-center justify-between gap-2 border-b border-slate-200 bg-white px-3 py-2">
        <div className="flex items-center gap-1 overflow-x-auto">
          {(
            [
              ["context", "Test Context"],
              ["result", "Result"],
              ["resolved", "Resolved Prompts"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setTestTab(id)}
              className={`whitespace-nowrap rounded-md px-3 py-1.5 text-xs font-medium ${
                testTab === id ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="hidden text-xs text-slate-500 sm:inline truncate max-w-[140px]" title={agentLabel}>
            {agentLabel}
          </span>
          <button type="button" onClick={onClose} className="rounded-md p-1 text-slate-500 hover:bg-slate-200" aria-label="Close test panel">
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-hidden bg-white">
        {testTab === "context" && (
          <div className="flex h-full flex-col p-3 sm:flex-row sm:gap-4">
            <div className="flex min-h-0 flex-1 flex-col">
              <label className="mb-2 flex items-center gap-2 text-xs font-semibold text-slate-700">
                <FileJson className="h-4 w-4 text-slate-400" />
                Test Context (JSON)
              </label>
              <textarea
                className="min-h-[120px] flex-1 w-full resize-none rounded-lg border border-slate-200 bg-white p-3 font-mono text-xs text-slate-700 shadow-inner focus:outline-none focus:ring-1 focus:ring-blue-500"
                value={testContext}
                onChange={(e) => setTestContext(e.target.value)}
              />
            </div>
            <div className="flex shrink-0 flex-col justify-end sm:w-40">
              <button
                type="button"
                onClick={() => testMutation.mutate()}
                disabled={testMutation.isPending}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50"
              >
                {testMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4 fill-white" />}
                {testMutation.isPending ? "Generating..." : "Run Agent"}
              </button>
            </div>
          </div>
        )}

        {testTab === "result" && (
          <div className="flex h-full flex-col">
            <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-3 py-2 text-xs text-slate-600">
              {result?.model_used && (
                <span className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5 font-mono">Model: {result.model_used}</span>
              )}
              {result?.cost != null && <span className="font-mono">Cost: ${Number(result.cost).toFixed(6)}</span>}
              {result?.usage?.total_tokens != null && (
                <span className="font-mono">Tokens: {result.usage.total_tokens}</span>
              )}
              {result?.usage?.prompt_tokens != null && result?.usage?.completion_tokens != null && (
                <span className="font-mono text-slate-500">
                  in {result.usage.prompt_tokens} / out {result.usage.completion_tokens}
                </span>
              )}
              {outputText && <CopyButton text={outputText} label="Copy" className="ml-auto" />}
            </div>
            <div className="relative min-h-0 flex-1">
              {testMutation.isPending && (
                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-white/60 backdrop-blur-[1px]">
                  <Loader2 className="mb-2 h-8 w-8 animate-spin text-blue-600" />
                  <span className="text-sm font-medium text-slate-500">Waiting for LLM...</span>
                </div>
              )}
              {!result && !testMutation.isPending && (
                <div className="flex h-full items-center justify-center text-sm italic text-slate-400">Run a test from the Test Context tab</div>
              )}
              {result && (
                <Editor
                  height="100%"
                  language={outputText.trim().startsWith("{") ? "json" : "markdown"}
                  theme="vs-light"
                  value={outputText}
                  options={{
                    readOnly: true,
                    minimap: { enabled: false },
                    wordWrap: "on",
                    padding: { top: 12 },
                    unusualLineTerminators: "off",
                  }}
                />
              )}
            </div>
          </div>
        )}

        {testTab === "resolved" && (
          <div className="h-full overflow-auto p-3">
            {!result?.resolved_prompts && !testMutation.isPending && (
              <div className="flex h-full items-center justify-center text-sm italic text-slate-400">
                Resolved prompts appear after you run a test
              </div>
            )}
            {testMutation.isPending && (
              <div className="flex h-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
              </div>
            )}
            {result?.resolved_prompts && (
              <div className="grid h-full min-h-[200px] gap-3 md:grid-cols-2">
                <div className="flex min-h-[180px] flex-col rounded-lg border border-slate-200 bg-slate-50">
                  <div className="flex items-center justify-between border-b border-slate-200 bg-slate-100 px-2 py-1 text-[10px] font-bold uppercase text-slate-600">
                    System (resolved)
                    <CopyButton text={result.resolved_prompts.system_prompt} className="h-7" />
                  </div>
                  <div className="min-h-0 flex-1">
                    <Editor
                      height="220px"
                      language="markdown"
                      theme="vs-light"
                      value={result.resolved_prompts.system_prompt}
                      options={{
                        readOnly: true,
                        minimap: { enabled: false },
                        wordWrap: "on",
                        padding: { top: 8 },
                        unusualLineTerminators: "off",
                      }}
                    />
                  </div>
                </div>
                <div className="flex min-h-[180px] flex-col rounded-lg border border-slate-200 bg-slate-50">
                  <div className="flex items-center justify-between border-b border-slate-200 bg-slate-100 px-2 py-1 text-[10px] font-bold uppercase text-slate-600">
                    User (resolved)
                    <CopyButton text={result.resolved_prompts.user_prompt} className="h-7" />
                  </div>
                  <div className="min-h-0 flex-1">
                    <Editor
                      height="220px"
                      language="markdown"
                      theme="vs-light"
                      value={result.resolved_prompts.user_prompt}
                      options={{
                        readOnly: true,
                        minimap: { enabled: false },
                        wordWrap: "on",
                        padding: { top: 8 },
                        unusualLineTerminators: "off",
                      }}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
