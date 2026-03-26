import sys
import os
import json

# Ensure app is in Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.prompt import Prompt

PROMPTS_DATA = [
    {
        "agent_name": "ai_structure_analysis",
        "model": "openai/gpt-4o",
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
        "temperature": 0.7,
        "system_prompt": "You are the final proofreader and formatter. Polish the prose.",
        "user_prompt": """Keyword: {{keyword}}
Language: {{language}}
Rhythms & Style: {{rhythms_style}}
Author Style: {{author_style}}

Excluded words: {{exclude_words}}

Text:
{{result_improver}}

Conduct a final polish. Ensure rhythms are crisp. Output the final HTML.""",
    },
    {
        "agent_name": "content_fact_checking",
        "model": "openai/gpt-4o",
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
        "model": "openai/gpt-4o",
        "temperature": 0.7,
        "system_prompt": "You are an expert Frontend Developer. You merge content into a base HTML template.",
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
        "temperature": 0.7,
        "system_prompt": "You are a Midjourney prompt engineer. You receive MULTIMEDIA block descriptors extracted from an article outline and transform each one into an optimized Midjourney v6 prompt.\nOutput ONLY a valid JSON object with an 'images' array.",
        "user_prompt": """Keyword: {{keyword}}
Language: {{language}}

Below are the MULTIMEDIA blocks extracted from the article outline. Each has an 'id', 'section', 'section_content', and a 'multimedia' object with Type, Description, etc.

[CONTEXT]

For each MULTIMEDIA block, generate a JSON array entry with:
- "id": same as block id
- "section": same section name
- "midjourney_prompt": optimized Midjourney v6 prompt (English, detailed, photorealistic or matching the Type). Include style keywords: --style raw, lighting, composition. Do NOT include --ar or --v flags (those are added automatically).
- "alt_text": SEO-friendly alt text in {{language}}
- "aspect_ratio": recommended ratio (e.g. "16:9", "4:3", "1:1")

Output JSON:
{
  "images": [
    {"id": "img_1", "section": "...", "midjourney_prompt": "...", "alt_text": "...", "aspect_ratio": "16:9"},
    ...
  ]
}

Respond with pure JSON only, without markdown wrapping.""",
    }
]

def seed():
    print("Starting prompt seeding...")
    db = SessionLocal()
    try:
        inserted = 0
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
                    is_active=True,
                    version=1
                )
                db.add(db_prompt)
                inserted += 1
                print(f"Created prompt for: {pdata['agent_name']}")
            else:
                skipped += 1
                print(f"Skipped existing prompt for: {pdata['agent_name']}")
        
        db.commit()
        print(f"Done. Inserted: {inserted}. Skipped: {skipped}.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding prompts: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
