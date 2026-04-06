/** Canonical pipeline step ids (keep in sync with backend `PIPELINE_PRESETS` / `ALL_STEPS`). */

export const PIPELINE_CUSTOM_CANONICAL_ORDER = [
  "serp_research",
  "competitor_scraping",
  "ai_structure_analysis",
  "chunk_cluster_analysis",
  "competitor_structure_analysis",
  "final_structure_analysis",
  "structure_fact_checking",
  "image_prompt_generation",
  "image_generation",
  "primary_generation",
  "primary_generation_about",
  "primary_generation_legal",
  "competitor_comparison",
  "reader_opinion",
  "interlinking_citations",
  "improver",
  "final_editing",
  "content_fact_checking",
  "html_structure",
  "image_inject",
  "meta_generation",
] as const;

export type PipelineStepId = (typeof PIPELINE_CUSTOM_CANONICAL_ORDER)[number];

export const CUSTOM_STEP_OPTIONS: { id: string; label: string }[] = [
  { id: "serp_research", label: "SERP Research" },
  { id: "competitor_scraping", label: "Competitor Scraping" },
  { id: "ai_structure_analysis", label: "AI Structure Analysis" },
  { id: "chunk_cluster_analysis", label: "Chunk Cluster Analysis" },
  { id: "competitor_structure_analysis", label: "Competitor Structure" },
  { id: "final_structure_analysis", label: "Final Structure Analysis" },
  { id: "structure_fact_checking", label: "Structure Fact-Checking" },
  { id: "image_prompt_generation", label: "Image Prompts (LLM)" },
  { id: "image_generation", label: "Image Creation" },
  { id: "primary_generation", label: "Primary Generation (standard)" },
  { id: "primary_generation_about", label: "Primary Generation (About Page)" },
  { id: "primary_generation_legal", label: "Primary Generation (Legal Page)" },
  { id: "competitor_comparison", label: "Competitor Comparison" },
  { id: "reader_opinion", label: "Reader Opinion" },
  { id: "interlinking_citations", label: "Interlinking & Citations" },
  { id: "improver", label: "Improver" },
  { id: "final_editing", label: "Final Editing" },
  { id: "content_fact_checking", label: "Content Fact-Checking" },
  { id: "html_structure", label: "HTML Structure" },
  { id: "image_inject", label: "Image Inject" },
  { id: "meta_generation", label: "Meta Generation" },
];

/** Default “full” preset step list for custom-mode prefill (matches backend `full`). */
export const DEFAULT_FULL_PIPELINE_STEPS: string[] = [
  "serp_research",
  "competitor_scraping",
  "ai_structure_analysis",
  "chunk_cluster_analysis",
  "competitor_structure_analysis",
  "final_structure_analysis",
  "structure_fact_checking",
  "primary_generation",
  "competitor_comparison",
  "reader_opinion",
  "improver",
  "final_editing",
  "html_structure",
  "meta_generation",
];

export function normalizeCustomPipelineSteps(selected: string[]): string[] {
  const set = new Set(selected);
  return PIPELINE_CUSTOM_CANONICAL_ORDER.filter((s) => set.has(s));
}

export function orderedStepKeysFromResults(stepResults: Record<string, unknown>): string[] {
  const plan = stepResults._pipeline_plan as { steps?: string[] } | undefined;
  if (plan?.steps?.length) {
    return plan.steps.filter((s) => typeof s === "string");
  }
  const skip = new Set(["waiting_for_approval", "test_mode_approved"]);
  const keys = Object.keys(stepResults).filter(
    (k) =>
      !k.startsWith("_") &&
      !k.endsWith("_prev_versions") &&
      !skip.has(k)
  );
  const ordered = PIPELINE_CUSTOM_CANONICAL_ORDER.filter((k) => keys.includes(k));
  const rest = keys.filter((k) => !PIPELINE_CUSTOM_CANONICAL_ORDER.includes(k as PipelineStepId));
  return [...ordered, ...rest.sort()];
}
