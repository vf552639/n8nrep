# Pipeline Steps Keys

STEP_SERP = "serp_research"
STEP_SCRAPING = "competitor_scraping"
STEP_AI_ANALYSIS = "ai_structure_analysis"
STEP_CHUNK_ANALYSIS = "chunk_cluster_analysis"
STEP_COMP_STRUCTURE = "competitor_structure_analysis"
STEP_FINAL_ANALYSIS = "final_structure_analysis"
STEP_STRUCTURE_FACT_CHECK = "structure_fact_checking"
STEP_IMAGE_PROMPT_GEN = "image_prompt_generation"
STEP_IMAGE_GEN = "image_generation"
STEP_PRIMARY_GEN = "primary_generation"
STEP_COMP_COMPARISON = "competitor_comparison"
STEP_READER_OPINION = "reader_opinion"
STEP_INTERLINK = "interlinking_citations"
STEP_IMPROVER = "improver"
STEP_FINAL_EDIT = "final_editing"
STEP_HTML_STRUCT = "html_structure"
STEP_IMAGE_INJECT = "image_inject"
STEP_META_GEN = "meta_generation"
STEP_CONTENT_FACT_CHECK = "content_fact_checking"

ALL_STEPS = [
    STEP_SERP,
    STEP_SCRAPING,
    STEP_AI_ANALYSIS,
    STEP_CHUNK_ANALYSIS,
    STEP_COMP_STRUCTURE,
    STEP_FINAL_ANALYSIS,
    STEP_STRUCTURE_FACT_CHECK,
    STEP_IMAGE_PROMPT_GEN,
    STEP_IMAGE_GEN,
    STEP_PRIMARY_GEN,
    STEP_COMP_COMPARISON,
    STEP_READER_OPINION,
    STEP_INTERLINK,
    STEP_IMPROVER,
    STEP_FINAL_EDIT,
    STEP_CONTENT_FACT_CHECK,
    STEP_HTML_STRUCT,
    STEP_IMAGE_INJECT,
    STEP_META_GEN
]

CRITICAL_VARS = {
    "ai_structure_analysis": ["keyword", "language", "country"],
    "chunk_cluster_analysis": ["keyword", "language", "country"],
    "competitor_structure_analysis": ["keyword", "language", "country"],
    "final_structure_analysis": ["keyword", "language", "country"],
    "image_prompt_generation": ["keyword", "language"],
    "primary_generation": ["keyword", "additional_keywords", "language"],
    "competitor_comparison": ["keyword"],
    "reader_opinion": ["keyword"],
    "interlinking_citations": ["keyword", "site_name"],
    "improver": ["keyword", "exclude_words"],
    "final_editing": ["keyword", "exclude_words"],
    "html_structure": ["keyword", "language"],
    "meta_generation": ["keyword", "language"],
    "structure_fact_checking": ["keyword", "result_final_structure_analysis"],
    "content_fact_checking": ["keyword", "language"],
}

