import re

from bs4 import BeautifulSoup, Comment

from app.services.json_parser import clean_and_parse_json
from app.services.pipeline.persistence import add_log
from app.services.pipeline.registry import register_step
from app.services.pipeline.steps.base import StepPolicy, StepResult
from app.services.pipeline_constants import STEP_HTML_STRUCT, STEP_IMAGE_GEN, STEP_IMAGE_INJECT
from app.services.word_counter import count_content_words


class ImageInjectStep:
    name = STEP_IMAGE_INJECT
    policy = StepPolicy()

    def run(self, ctx) -> StepResult:
        html_result = ctx.task.step_results.get(STEP_HTML_STRUCT, {}).get("result", "")
        if not html_result:
            add_log(ctx.db, ctx.task, "No HTML structure found — skipping image inject", step=STEP_IMAGE_INJECT)
            return StepResult(
                status="completed",
                result="",
                extra={"input_word_count": 0, "output_word_count": 0},
            )

        image_data_raw = ctx.task.step_results.get(STEP_IMAGE_GEN, {}).get("result", "")
        if not image_data_raw:
            add_log(ctx.db, ctx.task, "No image data — passing HTML through unchanged", step=STEP_IMAGE_INJECT)
            wc = count_content_words(html_result)
            return StepResult(
                status="completed",
                result=html_result,
                extra={"input_word_count": wc, "output_word_count": wc},
            )

        image_data = clean_and_parse_json(image_data_raw) if isinstance(image_data_raw, str) else image_data_raw
        if not isinstance(image_data, dict):
            wc = count_content_words(html_result)
            return StepResult(
                status="completed",
                result=html_result,
                extra={"input_word_count": wc, "output_word_count": wc},
            )

        approved_images = [
            img for img in image_data.get("images", []) if img.get("approved") is True and img.get("hosted_url")
        ]
        if not approved_images:
            add_log(
                ctx.db, ctx.task, "No approved images — cleaning MEDIA comment markers", step=STEP_IMAGE_INJECT
            )
            cleaned = re.sub(r"<!--\s*MEDIA:.*?-->", "", html_result, flags=re.IGNORECASE | re.DOTALL)
            in_w = count_content_words(html_result)
            out_w = count_content_words(cleaned)
            return StepResult(
                status="completed",
                result=cleaned,
                extra={"input_word_count": in_w, "output_word_count": out_w},
            )

        add_log(
            ctx.db,
            ctx.task,
            f"Injecting {len(approved_images)} approved images into HTML...",
            step=STEP_IMAGE_INJECT,
        )
        soup = BeautifulSoup(html_result, "html.parser")
        media_comments = [
            node for node in soup.find_all(string=lambda text: isinstance(text, Comment) and "MEDIA:" in str(text))
        ]
        injected_count = 0
        for i, img in enumerate(approved_images):
            hosted_url = img["hosted_url"]
            alt_text = img.get("alt_text", "")
            figure_html = (
                f'<figure class="article-image">'
                f'<img src="{hosted_url}" alt="{alt_text}" width="800" loading="lazy">'
                f"<figcaption>{alt_text}</figcaption>"
                f"</figure>"
            )
            figure_fragment = BeautifulSoup(figure_html, "html.parser")
            figure_node = figure_fragment.find("figure")
            if not figure_node:
                continue
            if i < len(media_comments):
                media_comments[i].replace_with(figure_node)
                injected_count += 1
            else:
                all_h2 = soup.find_all("h2")
                if all_h2:
                    all_h2[-1].insert_before(figure_node)
                    injected_count += 1

        result_html = str(soup)
        result_html = re.sub(r"<!--\s*MEDIA:.*?-->", "", result_html, flags=re.IGNORECASE | re.DOTALL)
        add_log(
            ctx.db,
            ctx.task,
            f"Image injection completed: {injected_count}/{len(approved_images)} inserted",
            step=STEP_IMAGE_INJECT,
        )
        in_w = count_content_words(html_result)
        out_w = count_content_words(result_html)
        return StepResult(
            status="completed",
            result=result_html,
            extra={"input_word_count": in_w, "output_word_count": out_w},
        )


register_step(ImageInjectStep())
