import { useState, useEffect, useMemo, useRef } from "react";
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
  Settings2,
  X,
  FileJson,
  Loader2,
  ChevronDown,
  Search,
  Copy,
  PanelRightOpen,
  History,
  RotateCcw,
} from "lucide-react";

const AGENT_MAP: Record<string, string> = {
  ai_structure_analysis: "AI Structure Analysis",
  chunk_cluster_analysis: "Chunk Cluster Analysis",
  competitor_structure_analysis: "Competitor Structure",
  final_structure_analysis: "Final Structure Analysis",
  structure_fact_checking: "Structure Fact-Checking",
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
    temperature: p.temperature ?? 0.7,
    frequency_penalty: p.frequency_penalty ?? 0,
    presence_penalty: p.presence_penalty ?? 0,
    top_p: p.top_p ?? 1,
    skip_in_pipeline: !!p.skip_in_pipeline,
  };
}

function isPromptDirty(edit: Partial<Prompt> | null, saved: Prompt | null | undefined, params: { freq: boolean; pres: boolean; top: boolean }) {
  if (!edit || !saved) return false;
  const e = normalizePrompt(edit);
  const s = normalizePrompt(saved);
  if (!e || !s) return false;
  if (e.system_prompt !== s.system_prompt || e.user_prompt !== s.user_prompt) return true;
  if (e.model !== s.model) return true;
  if (e.temperature !== s.temperature) return true;
  if (e.skip_in_pipeline !== s.skip_in_pipeline) return true;
  const effFreq = params.freq ? e.frequency_penalty : 0;
  const effPres = params.pres ? e.presence_penalty : 0;
  const effTop = params.top ? e.top_p : 1;
  const savFreq = (saved.frequency_penalty ?? 0) !== 0;
  const savPres = (saved.presence_penalty ?? 0) !== 0;
  const savTop = (saved.top_p ?? 1) !== 1;
  if (params.freq !== savFreq || params.pres !== savPres || params.top !== savTop) return true;
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
  const [paramsEnabled, setParamsEnabled] = useState({ freq: false, pres: false, top: false });
  const [variablesDrawerOpen, setVariablesDrawerOpen] = useState(false);
  const [versionMenuOpen, setVersionMenuOpen] = useState(false);
  const versionMenuRef = useRef<HTMLDivElement>(null);

  const knownAgents = Object.keys(AGENT_MAP);

  const { data: prompts, isLoading } = useQuery({
    queryKey: ["prompts"],
    queryFn: () => promptsApi.getAll(),
  });

  const filteredPrompts = prompts?.filter((p: Prompt) => knownAgents.includes(p.agent_name));
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

  const { data: versionRows } = useQuery({
    queryKey: ["prompt-versions", derivedActiveId],
    queryFn: () => (derivedActiveId ? promptsApi.getVersions(derivedActiveId) : Promise.resolve([])),
    enabled: !!derivedActiveId,
  });

  useEffect(() => {
    if (!activePromptId && derivedActiveId) {
      setActivePromptId(derivedActiveId);
    }
  }, [activePromptId, derivedActiveId]);

  useEffect(() => {
    if (fullPrompt && fullPrompt.id !== editState?.id) {
      const cleanPrompt = { ...fullPrompt };
      if (cleanPrompt.temperature !== undefined) cleanPrompt.temperature = Math.round(cleanPrompt.temperature * 10) / 10;
      if (cleanPrompt.frequency_penalty !== undefined) cleanPrompt.frequency_penalty = Math.round(cleanPrompt.frequency_penalty * 10) / 10;
      if (cleanPrompt.presence_penalty !== undefined) cleanPrompt.presence_penalty = Math.round(cleanPrompt.presence_penalty * 10) / 10;
      if (cleanPrompt.top_p !== undefined) cleanPrompt.top_p = Math.round(cleanPrompt.top_p * 10) / 10;

      setEditState(cleanPrompt);
      setParamsEnabled({
        freq: cleanPrompt.frequency_penalty !== undefined && cleanPrompt.frequency_penalty !== 0.0,
        pres: cleanPrompt.presence_penalty !== undefined && cleanPrompt.presence_penalty !== 0.0,
        top: cleanPrompt.top_p !== undefined && cleanPrompt.top_p !== 1.0,
      });
    }
  }, [fullPrompt, editState?.id]);

  const isDirty = useMemo(
    () => isPromptDirty(editState, fullPrompt ?? null, paramsEnabled),
    [editState, fullPrompt, paramsEnabled]
  );

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (versionMenuRef.current && !versionMenuRef.current.contains(e.target as Node)) {
        setVersionMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const saveMutation = useMutation({
    mutationFn: (data: Partial<Prompt>) => {
      const payload: Partial<Prompt> = {
        ...data,
        temperature: data.temperature ?? 0.7,
        frequency_penalty: paramsEnabled.freq ? (data.frequency_penalty ?? 0.0) : 0.0,
        presence_penalty: paramsEnabled.pres ? (data.presence_penalty ?? 0.0) : 0.0,
        top_p: paramsEnabled.top ? (data.top_p ?? 1.0) : 1.0,
      };
      return promptsApi.update(payload);
    },
    onSuccess: () => {
      toast.success("Prompt saved successfully");
      queryClient.invalidateQueries({ queryKey: ["prompts"] });
      queryClient.invalidateQueries({ queryKey: ["prompt", derivedActiveId] });
      queryClient.invalidateQueries({ queryKey: ["prompt-versions", derivedActiveId] });
    },
    onError: () => toast.error("Failed to save prompt"),
  });

  const restoreMutation = useMutation({
    mutationFn: ({ baseId, sourceId }: { baseId: string; sourceId: string }) =>
      promptsApi.restoreVersion(baseId, sourceId),
    onSuccess: (data: { id: string; version: number }) => {
      toast.success(`Restored as v${data.version}`);
      setVersionMenuOpen(false);
      setActivePromptId(data.id);
      queryClient.invalidateQueries({ queryKey: ["prompts"] });
      queryClient.invalidateQueries({ queryKey: ["prompt", data.id] });
      queryClient.invalidateQueries({ queryKey: ["prompt-versions", data.id] });
    },
    onError: () => toast.error("Failed to restore version"),
  });

  const requestSelectAgent = (nextId: string) => {
    if (nextId === activePromptId) return;
    if (isDirty) {
      if (!window.confirm("You have unsaved changes. Switch agent and discard edits?")) return;
    }
    setActivePromptId(nextId);
    setIsTestOpen(false);
  };

  const variableExplorerInner = (
    <>
      <div className="p-3 border-b">
        <div className="relative">
          <Search className="absolute left-2.5 top-2 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search..."
            value={variablesQuery}
            onChange={(e) => setVariablesQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 text-xs border border-slate-200 rounded-md bg-white shadow-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
          {variablesQuery && (
            <button
              type="button"
              onClick={() => setVariablesQuery("")}
              className="absolute right-2.5 top-2 h-4 w-4 text-slate-400 hover:text-slate-600"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-auto p-3 space-y-5 min-h-0">
        {PROMPT_VARIABLES.map((group) => {
          const filteredVars = group.vars.filter(
            (v) =>
              v.name.toLowerCase().includes(variablesQuery.toLowerCase()) ||
              v.desc.toLowerCase().includes(variablesQuery.toLowerCase())
          );

          if (filteredVars.length === 0) return null;

          return (
            <div key={group.group} className="space-y-2">
              <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2 border-b border-slate-100 pb-1">
                {group.group}
              </h4>
              <div className="space-y-1.5">
                {filteredVars.map((v) => (
                  <div key={v.name} className="flex flex-col text-[11px] group/var">
                    <button
                      type="button"
                      onClick={() => {
                        navigator.clipboard.writeText(`{{${v.name}}}`);
                        toast.success(`Copied {{${v.name}}}`);
                      }}
                      className="flex items-center text-[10px] justify-between font-mono text-blue-700 bg-blue-50/50 px-2 py-1 rounded border border-blue-100 hover:bg-blue-100 transition-colors cursor-pointer text-left w-full relative"
                      title="Click to copy"
                    >
                      <span className="truncate pr-4">{`{{${v.name}}}`}</span>
                      <Copy className="w-3 h-3 text-blue-400 opacity-0 group-hover/var:opacity-100 transition-opacity shrink-0 absolute right-1.5" />
                    </button>
                    <span className="text-slate-500 mt-[2px] px-1 truncate leading-tight" title={v.desc}>
                      {v.desc}
                    </span>
                  </div>
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
        ) && <div className="text-xs text-slate-500 text-center py-4">No variables found</div>}
      </div>
    </>
  );

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-2 xl:gap-4 min-h-0">
      <div className="w-[220px] bg-white border rounded-lg shadow-sm flex flex-col shrink-0 min-h-0">
        <div className="p-4 border-b bg-slate-50 font-semibold text-slate-800 rounded-t-lg">Available Agents</div>
        <div className="flex-1 overflow-auto p-2 space-y-1 min-h-0">
          {isLoading ? (
            <div className="p-4 text-center text-sm text-slate-500">Loading prompts...</div>
          ) : (
            filteredPrompts?.map((prompt: Prompt) => {
              const selected = (activePromptId ? activePromptId === prompt.id : filteredPrompts[0]?.id === prompt.id);
              const skipped = prompt.skip_in_pipeline;
              const dotClass = skipped ? "bg-amber-500" : selected ? "bg-emerald-500" : "bg-slate-400";
              return (
                <button
                  key={prompt.id}
                  type="button"
                  onClick={() => requestSelectAgent(prompt.id)}
                  className={`w-full text-left px-3 py-2.5 rounded-md text-sm transition-colors flex items-start gap-2 ${
                    selected ? "bg-blue-50 text-blue-700 font-medium ring-1 ring-blue-200" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  }`}
                >
                  <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${dotClass}`} aria-hidden />
                  <span className={`min-w-0 flex-1 ${skipped ? "line-through text-amber-800/90" : ""}`}>
                    {AGENT_MAP[prompt.agent_name] || prompt.agent_name.replace(/_/g, " ")}
                  </span>
                </button>
              );
            })
          )}
        </div>
      </div>

      <div className="flex-1 bg-white border rounded-lg shadow-sm flex flex-col min-w-0 min-h-0">
        {activePromptListInfo && editState && !isLoadingPrompt ? (
          <>
            <div className="p-4 border-b flex flex-col xl:flex-row justify-between items-start xl:items-center bg-slate-50 rounded-t-lg shrink-0 gap-4">
              <div className="flex flex-wrap items-center gap-2 min-w-0">
                <h2 className="font-semibold text-slate-800 capitalize text-lg truncate">
                  {AGENT_MAP[activePromptListInfo.agent_name] || activePromptListInfo.agent_name.replace(/_/g, " ")}
                </h2>
                <div className="relative" ref={versionMenuRef}>
                  <button
                    type="button"
                    onClick={() => setVersionMenuOpen((o) => !o)}
                    className="inline-flex items-center gap-1 rounded-full bg-slate-200/80 px-2.5 py-0.5 text-xs font-semibold text-slate-800 hover:bg-slate-300/80"
                  >
                    v{activePromptListInfo.version}
                    <ChevronDown className="h-3.5 w-3.5 opacity-70" />
                  </button>
                  {versionMenuOpen && versionRows && versionRows.length > 0 && (
                    <div className="absolute left-0 z-50 mt-1 w-72 rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
                      <div className="flex items-center gap-2 border-b border-slate-100 px-3 py-2 text-xs font-semibold text-slate-600">
                        <History className="h-3.5 w-3.5" />
                        Version history
                      </div>
                      <div className="max-h-64 overflow-auto">
                        {versionRows.map((row) => (
                          <div
                            key={row.id}
                            className="flex items-center justify-between gap-2 px-3 py-2 text-sm hover:bg-slate-50"
                          >
                            <div className="min-w-0">
                              <span className="font-mono font-medium">v{row.version}</span>
                              {row.is_active && (
                                <span className="ml-2 rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-800">
                                  current
                                </span>
                              )}
                              {row.updated_at && (
                                <div className="truncate text-[11px] text-slate-400">{row.updated_at}</div>
                              )}
                            </div>
                            {!row.is_active && derivedActiveId && (
                              <button
                                type="button"
                                disabled={restoreMutation.isPending}
                                onClick={() =>
                                  restoreMutation.mutate({ baseId: derivedActiveId, sourceId: row.id })
                                }
                                className="inline-flex shrink-0 items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100"
                              >
                                <RotateCcw className="h-3.5 w-3.5" />
                                Restore
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex w-full items-center justify-end gap-2 xl:hidden">
                <button
                  type="button"
                  onClick={() => setVariablesDrawerOpen(true)}
                  className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
                >
                  <PanelRightOpen className="h-4 w-4" />
                  Variables ({VAR_COUNT})
                </button>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 space-y-4 w-full xl:w-[500px] shrink-0">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                  <Settings2 className="w-4 h-4 text-slate-400" />
                  Model Settings
                </div>

                <div className="flex flex-col gap-1 w-full">
                  <label className="text-xs text-slate-500 font-medium">Model</label>
                  <ModelSelector
                    value={editState.model || "openai/gpt-4o"}
                    models={orModels || ["openai/gpt-4o"]}
                    onChange={(m) => setEditState((prev) => (prev ? { ...prev, model: m } : null))}
                  />
                </div>

                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  <div className="bg-slate-50 rounded-lg p-3 border border-slate-100 flex flex-col justify-between">
                    <label className="flex items-center gap-2 text-[11px] font-medium text-slate-600 mb-2 whitespace-nowrap">
                      <input type="checkbox" className="rounded border-slate-300 text-blue-600 cursor-not-allowed" checked readOnly />
                      Temperature
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      max="2"
                      value={editState.temperature ?? 0.7}
                      onChange={(e) => setEditState((prev) => (prev ? { ...prev, temperature: parseFloat(e.target.value) } : null))}
                      onBlur={(e) => {
                        const val = Math.min(Math.max(Math.round(parseFloat(e.target.value) * 10) / 10, 0), 2);
                        setEditState((prev) => (prev ? { ...prev, temperature: val } : null));
                      }}
                      className="w-full text-sm border border-slate-200 rounded-md px-2 py-1.5 text-right font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                    />
                  </div>

                  <div className="bg-slate-50 rounded-lg p-3 border border-slate-100 flex flex-col justify-between">
                    <label className="flex items-center gap-2 text-[11px] font-medium text-slate-600 cursor-pointer mb-2 whitespace-nowrap">
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
                      Freq. Penalty
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      min="-2"
                      max="2"
                      disabled={!paramsEnabled.freq}
                      value={editState.frequency_penalty ?? 0.0}
                      onChange={(e) => setEditState((prev) => (prev ? { ...prev, frequency_penalty: parseFloat(e.target.value) } : null))}
                      onBlur={(e) => {
                        const val = Math.min(Math.max(Math.round(parseFloat(e.target.value) * 10) / 10, -2), 2);
                        setEditState((prev) => (prev ? { ...prev, frequency_penalty: val } : null));
                      }}
                      className="w-full text-sm border border-slate-200 rounded-md px-2 py-1.5 text-right font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none disabled:opacity-40 disabled:bg-slate-100"
                    />
                  </div>

                  <div className="bg-slate-50 rounded-lg p-3 border border-slate-100 flex flex-col justify-between">
                    <label className="flex items-center gap-2 text-[11px] font-medium text-slate-600 cursor-pointer mb-2 whitespace-nowrap">
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
                      Pres. Penalty
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      min="-2"
                      max="2"
                      disabled={!paramsEnabled.pres}
                      value={editState.presence_penalty ?? 0.0}
                      onChange={(e) => setEditState((prev) => (prev ? { ...prev, presence_penalty: parseFloat(e.target.value) } : null))}
                      onBlur={(e) => {
                        const val = Math.min(Math.max(Math.round(parseFloat(e.target.value) * 10) / 10, -2), 2);
                        setEditState((prev) => (prev ? { ...prev, presence_penalty: val } : null));
                      }}
                      className="w-full text-sm border border-slate-200 rounded-md px-2 py-1.5 text-right font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none disabled:opacity-40 disabled:bg-slate-100"
                    />
                  </div>

                  <div className="bg-slate-50 rounded-lg p-3 border border-slate-100 flex flex-col justify-between">
                    <label className="flex items-center gap-2 text-[11px] font-medium text-slate-600 cursor-pointer mb-2 whitespace-nowrap">
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
                      Top P
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      max="1"
                      disabled={!paramsEnabled.top}
                      value={editState.top_p ?? 1.0}
                      onChange={(e) => setEditState((prev) => (prev ? { ...prev, top_p: parseFloat(e.target.value) } : null))}
                      onBlur={(e) => {
                        const val = Math.min(Math.max(Math.round(parseFloat(e.target.value) * 10) / 10, 0), 1);
                        setEditState((prev) => (prev ? { ...prev, top_p: val } : null));
                      }}
                      className="w-full text-sm border border-slate-200 rounded-md px-2 py-1.5 text-right font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none disabled:opacity-40 disabled:bg-slate-100"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between border-t border-slate-200 pt-4 mt-2">
                  <label className="flex items-center gap-2 text-[13px] font-medium text-slate-700 cursor-pointer group">
                    <input
                      type="checkbox"
                      className="rounded border-orange-300 text-orange-500 focus:ring-orange-500 cursor-pointer"
                      checked={editState.skip_in_pipeline || false}
                      onChange={(e) => setEditState((prev) => (prev ? { ...prev, skip_in_pipeline: e.target.checked } : null))}
                    />
                    Skip in pipeline
                  </label>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setIsTestOpen((o) => !o);
                        if (isTestOpen) setTestTab("context");
                      }}
                      className={`flex items-center gap-2 px-4 py-1.5 rounded-md transition-colors text-sm font-medium border ${
                        isTestOpen ? "bg-blue-100 text-blue-800 border-blue-300" : "bg-slate-100 text-slate-700 hover:bg-slate-200 border-slate-200"
                      }`}
                    >
                      <Play className="w-4 h-4" /> Test
                    </button>
                    <button
                      type="button"
                      onClick={() => saveMutation.mutate(editState)}
                      disabled={saveMutation.isPending || !isDirty}
                      className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-1.5 rounded-md transition-colors text-sm font-medium shadow-sm disabled:opacity-70"
                    >
                      <Save className="w-4 h-4" />
                      {isDirty ? "Save*" : "Save"}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
              <div className="flex-1 flex flex-col xl:flex-row min-h-0 divide-y xl:divide-y-0 xl:divide-x overflow-hidden">
                <div className="flex-1 flex flex-col min-h-[200px] min-w-0">
                  <div className="p-2.5 bg-slate-100 text-xs font-bold text-slate-600 uppercase tracking-wider shrink-0 border-b">
                    System Prompt
                  </div>
                  <div className="flex-1 relative bg-[#fffffe] min-h-0">
                    <Editor
                      height="100%"
                      language="markdown"
                      theme="vs-light"
                      value={editState.system_prompt || ""}
                      onChange={(val) => setEditState((prev) => (prev ? { ...prev, system_prompt: val || "" } : null))}
                      options={{ minimap: { enabled: false }, wordWrap: "on", padding: { top: 16 } }}
                    />
                  </div>
                </div>
                <div className="flex-1 flex flex-col min-h-[200px] min-w-0">
                  <div className="p-2.5 bg-slate-100 text-xs font-bold text-slate-600 uppercase tracking-wider shrink-0 border-b">
                    User Prompt
                  </div>
                  <div className="flex-1 relative bg-[#fffffe] min-h-0">
                    <Editor
                      height="100%"
                      language="markdown"
                      theme="vs-light"
                      value={editState.user_prompt || ""}
                      onChange={(val) => setEditState((prev) => (prev ? { ...prev, user_prompt: val || "" } : null))}
                      options={{ minimap: { enabled: false }, wordWrap: "on", padding: { top: 16 } }}
                    />
                  </div>
                </div>
              </div>

              {isTestOpen && editState.id && (
                <PromptTestPanel
                  promptId={editState.id}
                  model={editState.model || "openai/gpt-4o"}
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

      <div className="hidden xl:flex w-[280px] bg-white border rounded-lg shadow-sm flex-col shrink-0 min-h-0">
        <div className="p-3 border-b bg-slate-50 font-semibold text-slate-800 rounded-t-lg flex items-center justify-between shrink-0">
          <span className="text-sm">Available Variables</span>
          <span className="text-xs text-slate-500 bg-slate-200 px-1.5 py-0.5 rounded-md">{VAR_COUNT}</span>
        </div>
        <div className="flex flex-col flex-1 min-h-0">{variableExplorerInner}</div>
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
              <span className="text-sm font-semibold text-slate-800">Variables ({VAR_COUNT})</span>
              <button
                type="button"
                onClick={() => setVariablesDrawerOpen(false)}
                className="rounded-md p-1 text-slate-500 hover:bg-slate-200"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="flex flex-1 flex-col min-h-0 overflow-hidden">{variableExplorerInner}</div>
          </div>
        </div>
      )}
    </div>
  );
}

function PromptTestPanel({
  promptId,
  model,
  agentLabel,
  testTab,
  setTestTab,
  onClose,
}: {
  promptId: string;
  model: string;
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
                  options={{ readOnly: true, minimap: { enabled: false }, wordWrap: "on", padding: { top: 12 } }}
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
                      options={{ readOnly: true, minimap: { enabled: false }, wordWrap: "on", padding: { top: 8 } }}
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
                      options={{ readOnly: true, minimap: { enabled: false }, wordWrap: "on", padding: { top: 8 } }}
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
