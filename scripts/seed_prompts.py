import sys
import os

# Ensure app is in Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.prompt import Prompt

# Re-apply model/text/max_tokens from seed when running `python scripts/seed_prompts.py`
PROMPTS_FORCE_UPDATE = frozenset({"image_prompt_generation", "image_generation", "html_structure"})

PROMPTS_DATA = [
    {
        "agent_name": "ai_structure_analysis",
        "model": "openai/gpt-4o",
        "max_tokens": 8000,
        "temperature": 0.7,
        "system_prompt": "You are an expert SEO structure analyst. Your goal is to analyze the keyword and the SERP context to determine the best structure for a new article.\nRespond ONLY with a valid JSON document.",
        "user_prompt": """Analyze the following SEO request and SERP data:
Keyword: {{keyword}}
Language: {{language}}
Country: {{country}}

Competitors Headers:
{{competitors_headers}}

Merged Markdown (Sample):
{{merged_markdown}}

PAA:
{{paa_with_answers}}

Featured Snippet:
{{featured_snippet}}

Knowledge Graph:
{{knowledge_graph}}

Search Intent Signals:
{{search_intent_signals}}

Based on this, generate a JSON object with strictly these keys:
{
  "intent": "Search intent analysis",
  "Taxonomy": "Topic category",
  "Attention": "Key aspects to focus on to beat competitors",
  "structura": "High-level structure recommendation (e.g. H2s, H3s)"
}

Respond with pure JSON only, without markdown wrapping.""",
    },
    {
        "agent_name": "chunk_cluster_analysis",
        "model": "openai/gpt-4o",
        "max_tokens": 4000,
        "temperature": 0.7,
        "system_prompt": "You are a content analyst. Cluster the content headings and topics of competitors into a logical flow of information.",
        "user_prompt": """Keyword: {{keyword}}
Language: {{language}}

Competitor Content Chunk:
{{merged_markdown}}

Competitor Headers:
{{competitors_headers}}

Group these headings and snippets into thematic clusters. What are the core topics everyone covers, and what are the unique topics?""",
    },
    {
        "agent_name": "competitor_structure_analysis",
        "model": "openai/gpt-4o",
        "max_tokens": 4000,
        "temperature": 0.7,
        "system_prompt": "You are a top-tier structural editor. Analyze competitor structures to find their weaknesses and strengths.",
        "user_prompt": """Keyword: {{keyword}}
Language: {{language}}
Avg word count: {{avg_word_count}}

Competitor structural breakdown:
{{competitors_headers}}

Provide a detailed analysis of their structures. What's missing? How can we create a comprehensively better structure?""",
    },
    {
        "agent_name": "final_structure_analysis",
        "model": "openai/gpt-4o",
        "max_tokens": 8000,
        "temperature": 0.7,
        "system_prompt": "You are the final structural architect. You combine multiple analyses to produce a concrete outline for the article.\nRespond ONLY with a valid JSON document.",
        "user_prompt": """Keyword: {{keyword}} ({{page_type}})
Language: {{language}}

AI Structure Analysis:
{{result_ai_structure_analysis}}

Cluster Analysis:
{{result_chunk_cluster_analysis}}

Competitor Structure Analysis:
{{result_competitor_structure_analysis}}

Based on this, create the final, best-in-class outline. Respond ONLY with a JSON array representing the outline. Example format:
[
  {"level": "H1", "title": "...", "instructions": "...", "word_count": 200},
  {"level": "H2", "title": "...", "instructions": "...", "word_count": 350}
]

Respond with pure JSON only, without markdown wrapping.""",
    },
    {
        "agent_name": "structure_fact_checking",
        "model": "openai/gpt-4o",
        "max_tokens": 4000,
        "temperature": 0.7,
        "system_prompt": "You are a meticulous fact-checker.",
        "user_prompt": """Keyword: {{keyword}}
Language: {{language}}

Review the following proposed outline for logical errors, missing essential facts, or hallucinations.

Outline:
{{result_final_structure_analysis}}

Output a short report on what needs fixing, or 'PASSED' if it's perfect.""",
    },
    {
        "agent_name": "primary_generation",
        "model": "openai/gpt-4o",
        "max_tokens": 16000,
        "temperature": 0.8,
        "system_prompt": "You are a master content creator. Write the article in HTML format, following the provided instructions and style identically seamlessly.",
        "user_prompt": """Keyword: {{keyword}} ({{page_type}})
Language: {{language}}
Additional Keywords: {{additional_keywords}}

Author info: {{author}} - {{author_style}}
Tone/Mimicry: {{imitation}} ({{year}})
POV: {{face}}
Target Audience: {{target_audience}}
Style & Rhythms: {{rhythms_style}}

Excluded words (DO NOT USE): {{exclude_words}}

Draft the full article exactly following this outline:
{{result_final_structure_analysis}}

Use proper HTML tags (<h1>, <h2>, <p>, <ul>...). Output pure HTML.""",
    },
    {
        "agent_name": "competitor_comparison",
        "model": "openai/gpt-4o",
        "max_tokens": 4000,
        "temperature": 0.7,
        "system_prompt": "You are a critical reviewer comparing two pieces of content.",
        "user_prompt": """Keyword: {{keyword}}
Language: {{language}}

Our Generated Article:
{{result_primary_generation}}

Competitor Headers:
{{competitors_headers}}

Competitor Markdown Fragment:
{{merged_markdown}}

Compare our article vs competitors. Identify 3 specific areas where our article could be subjectively or factually stronger.""",
    },
    {
        "agent_name": "reader_opinion",
        "model": "openai/gpt-4o",
        "max_tokens": 4000,
        "temperature": 0.7,
        "system_prompt": "You simulate the target audience of the article.",
        "user_prompt": """Keyword: {{keyword}}
Language: {{language}}
Target Audience: {{target_audience}}

Read this draft:
{{result_primary_generation}}

As a member of the target audience, provide ruthless feedback on readability, engagement, and whether it solves your intent.""",
    },
    {
        "agent_name": "interlinking_citations",
        "model": "openai/gpt-4o",
        "max_tokens": 4000,
        "temperature": 0.7,
        "system_prompt": "You are an internal linking specialist.",
        "user_prompt": """Keyword: {{keyword}}
Site: {{site_name}}

Original Text:
{{result_primary_generation}}

Improve the original text by adding natural HTML <a> links where suitable, assuming standard site structure. Return the updated HTML. Do not alter the core message.""",
    },
    {
        "agent_name": "improver",
        "model": "openai/gpt-4o",
        "max_tokens": 16000,
        "temperature": 0.8,
        "system_prompt": "You are an executive editor. You synthesize feedback and improve the draft.",
        "user_prompt": """Original Text:
{{result_interlinking_citations}}

Feedback to incorporate:
- Competitor Gap Analysis: {{result_competitor_comparison}}
- Reader Opinion: {{result_reader_opinion}}
- Structure Check: {{structure_fact_checking}}

Excluded words: {{exclude_words}}

Improve the HTML text significantly. Ensure you address the feedback. Output pure HTML.""",
    },
    {
        "agent_name": "final_editing",
        "model": "openai/gpt-4o",
        "max_tokens": 16000,
        "temperature": 0.7,
        "system_prompt": "You are the final proofreader and formatter. Polish the prose and keep the article aligned with the approved outline where it matters for structure.",
        "user_prompt": """Keyword: {{keyword}}
Language: {{language}}
Rhythms & Style: {{rhythms_style}}
Author Style: {{author_style}}

Excluded words: {{exclude_words}}

Approved structure (outline) — use for structural alignment; do not paste it into the article:
{{result_final_structure_analysis}}

Article HTML to polish:
{{result_improver}}

Conduct a final polish. Verify headings/sections reflect the outline where applicable. Keep rhythms crisp. Output the final HTML only (no outline repetition).""",
    },
    {
        "agent_name": "content_fact_checking",
        "model": "openai/gpt-4o",
        "max_tokens": 4000,
        "temperature": 0.7,
        "system_prompt": "You are a stringent fact-checker.",
        "user_prompt": """Keyword: {{keyword}}
Language: {{language}}

Text:
{{result_final_editing}}

Identify any factual discrepancies or unsubstantiated claims in the text. Provide a short report.""",
    },
    {
        "agent_name": "html_structure",
        "model": "google/gemini-2.5-flash",
        "max_tokens": 16000,
        "temperature": 0.3,
        "system_prompt": """You are an expert Frontend Developer. You merge content into a base HTML template.

CRITICAL RULE: You MUST preserve ALL content from the input article word-for-word.
Do NOT summarize, shorten, or omit any paragraphs, lists, or sections.
Your job is ONLY to wrap the existing content in the HTML template structure.
The output MUST contain every sentence from the input article.""",
        "user_prompt": """Site: {{site_name}}
Template Name: {{site_template_name}}

Base HTML Template:
{{site_template_html}}

Content to insert:
{{result_final_editing}}

Insert the content into the most logical container (e.g., `<main>`, `<article>`, `<div id="content">`). Output the complete combined HTML document.""",
    },
    {
        "agent_name": "meta_generation",
        "model": "openai/gpt-4o",
        "max_tokens": 1000,
        "temperature": 0.7,
        "system_prompt": "You are an SEO meta tag generator. Output JSON only.",
        "user_prompt": """Keyword: {{keyword}}
Language: {{language}}

Final Content Snippet:
{{result_final_editing}}

Competitor Titles:
{{competitor_titles}}

Competitor Descriptions:
{{competitor_descriptions}}

Generate an optimized `title` and `description` for this page. Output pure JSON:
{
  "title": "Optimized Page Title",
  "description": "Optimized meta description"
}

Respond with pure JSON only, without markdown wrapping.""",
    },
    {
        "agent_name": "image_prompt_generation",
        "model": "openai/gpt-4o",
        "max_tokens": 2000,
        "temperature": 0.7,
        "system_prompt": """You are a professional graphic designer specializing in web assets for iGaming and online casino review websites.

You will receive a task containing:
- TYPE: the kind of visual (Image or Infographic)
- DESCRIPTION: what the image should depict
- PURPOSE: how this image will be used on the page
- SECTION CONTEXT: the article section title this image belongs to

Your job is to generate a visually compelling image following these rules:

GENERAL RULES:
1. Output a single, self-contained image. No multi-panel compositions unless the type is "Infographic".
2. Landscape orientation, 16:9 aspect ratio.
3. Modern, clean, professional web design aesthetic.
4. Rich but not overwhelming color palette. Default to dark/neon theme (deep navy, electric blue, neon green accents) unless the description explicitly states otherwise.
5. NO real brand logos, trademarks, or copyrighted UI screenshots. Create abstract/stylized representations instead.
6. NO human faces or realistic human depictions (to avoid likeness and compliance issues).
7. NO text, words, letters, or numbers baked into the image. All text will be overlaid in HTML/CSS later. Exception: if the type is "Infographic", you may include SHORT labels (1-3 words per label, max 5 labels total) as part of the visual flow.

TYPE-SPECIFIC RULES:

If TYPE = "Image":
- Create a single hero-style visual or section illustration.
- Focus on atmosphere, mood, and thematic relevance to the section.
- Think editorial photography style but digitally composed - abstract casino elements (chips, cards, coins, dice) arranged artistically, glowing interfaces, futuristic dashboards.
- Depth of field and lighting effects encouraged.

If TYPE = "Infographic":
- Create a visual flowchart or step-by-step diagram.
- Use icons, arrows, numbered steps, and visual connectors.
- Keep the layout left-to-right or top-to-bottom, logical reading order.
- Short labels ARE allowed (e.g., "Step 1", "Sign Up", "Confirm").
- Flat design or isometric style preferred.
- Each step should be visually distinct (different icon/color).

WHAT TO AVOID:
- Photorealistic casino interiors (compliance risk)
- Real currency bills or coins with identifiable national symbols
- Anything that could be interpreted as promoting gambling to minors
- Cluttered compositions - whitespace is your friend
- Generic stock-photo aesthetic - aim for distinctive, editorial quality

QUALITY:
- Render at highest available resolution
- Sharp edges, no artifacts
- Consistent lighting and shadow direction

RESPONSE FORMAT (STRICT):
You MUST respond with a valid JSON object containing EXACTLY these keys and no others:
{
  "image_prompt": "your detailed English visual description for the image model",
  "alt_text": "short description for img alt attribute",
  "aspect_ratio": "16:9"
}

For backward compatibility you may also include "midjourney_prompt" with the same text as "image_prompt"; if only one is present, it will be used.

Do not include any text outside the JSON object.
The "image_prompt" value must be a detailed English visual description for AI image generation (no vendor-specific flags), minimum 30 words. Aspect ratio is a separate field — do not append --ar or similar to the prompt text.""",
        "user_prompt": """Create a {{type}} for a web article section.

Section title: "{{parent_title}}"

Visual description: {{description}}

This image serves the following purpose on the page: {{purpose}}

Additional context:
- This is for an online casino review website targeting Australian audience
- The site uses a dark theme with neon accent colors
- The image will be displayed as a full-width block between text sections""",
    },
    {
        "agent_name": "image_generation",
        "model": "google/gemini-2.5-flash-image-preview",
        "temperature": 0.7,
        "system_prompt": "Service step (no chat prompt): the model id below is passed to OpenRouter image generation. Pick a model that lists image in output_modalities on OpenRouter (e.g. Gemini Flash Image, FLUX, Riverflow).",
        "user_prompt": "Unused — the pipeline sends prompts from the image_prompt_generation step directly to OpenRouter.",
    },
]

def seed():
    print("Starting prompt seeding...")
    db = SessionLocal()
    try:
        inserted = 0
        updated = 0
        skipped = 0
        for pdata in PROMPTS_DATA:
            existing = db.query(Prompt).filter(Prompt.agent_name == pdata["agent_name"], Prompt.is_active == True).first()
            if not existing:
                db_prompt = Prompt(
                    agent_name=pdata["agent_name"],
                    system_prompt=pdata["system_prompt"],
                    user_prompt=pdata["user_prompt"],
                    model=pdata["model"],
                    temperature=pdata["temperature"],
                    max_tokens=pdata.get("max_tokens"),
                    is_active=True,
                    version=1,
                )
                db.add(db_prompt)
                inserted += 1
                print(f"Created prompt for: {pdata['agent_name']}")
            elif pdata["agent_name"] in PROMPTS_FORCE_UPDATE:
                existing.system_prompt = pdata["system_prompt"]
                existing.user_prompt = pdata["user_prompt"]
                existing.model = pdata["model"]
                existing.temperature = pdata["temperature"]
                if "max_tokens" in pdata:
                    existing.max_tokens = pdata["max_tokens"]
                updated += 1
                print(f"Updated prompt for: {pdata['agent_name']}")
            else:
                skipped += 1
                print(f"Skipped existing prompt for: {pdata['agent_name']}")
        
        db.commit()
        print(f"Done. Inserted: {inserted}. Updated: {updated}. Skipped: {skipped}.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding prompts: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
