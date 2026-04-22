"""
Image generation — OpenRouter image models (FLUX, Gemini Image, Riverflow, etc.).
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import requests

from app.config import settings

OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"

# Image-only output (no assistant text): FLUX, Sourceful Riverflow, etc.
_IMAGE_ONLY_PREFIXES = (
    "black-forest-labs/",
    "sourceful/",
)


def modalities_for_model(model_id: str) -> list[str]:
    mid = (model_id or "").lower()
    for prefix in _IMAGE_ONLY_PREFIXES:
        if mid.startswith(prefix):
            return ["image"]
    return ["image", "text"]


def resolve_image_generation_model(db) -> str:
    """Model from active Prompt `image_generation`, else IMAGE_MODEL_DEFAULT."""
    from app.models.prompt import Prompt

    p = db.query(Prompt).filter(Prompt.agent_name == "image_generation", Prompt.is_active.is_(True)).first()
    if p and getattr(p, "model", None) and str(p.model).strip():
        return str(p.model).strip()
    return settings.IMAGE_MODEL_DEFAULT


@dataclass
class ImageResult:
    status: str  # "pending" | "processing" | "completed" | "failed"
    provider_task_id: str = ""
    image_url: str | None = None  # optional data URL or remote URL (legacy)
    hosted_url: str | None = None
    error: str | None = None


class ImageGeneratorBase(ABC):
    @abstractmethod
    def generate_and_wait(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        model: str | None = None,
    ) -> ImageResult:
        """Generate an image synchronously; return final ImageResult."""


def _normalize_aspect_for_config(aspect_ratio: str) -> str:
    ar = (aspect_ratio or "16:9").strip()
    allowed = {
        "1:1",
        "2:3",
        "3:2",
        "3:4",
        "4:3",
        "4:5",
        "5:4",
        "9:16",
        "16:9",
        "21:9",
    }
    return ar if ar in allowed else "16:9"


def extract_image_data_url_from_openrouter_response(data: dict[str, Any]) -> str | None:
    """Parse OpenRouter chat/completions JSON; return first image as data:... URL."""
    if not isinstance(data, dict):
        return None
    err = data.get("error")
    if err:
        if isinstance(err, dict):
            msg = err.get("message") or str(err)
        else:
            msg = str(err)
        raise RuntimeError(msg)

    choices = data.get("choices") or []
    if not choices:
        return None
    msg = choices[0].get("message") or {}
    images = msg.get("images") or []
    for img in images:
        if not isinstance(img, dict):
            continue
        url_obj = img.get("image_url") or img.get("imageUrl")
        if isinstance(url_obj, dict):
            u = url_obj.get("url")
            if isinstance(u, str) and u.startswith("data:"):
                return u
        if isinstance(url_obj, str) and url_obj.startswith("data:"):
            return url_obj
    content = msg.get("content")
    if isinstance(content, str):
        m = re.search(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", content)
        if m:
            return m.group(0)
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "image_url":
                uo = part.get("image_url") or {}
                if isinstance(uo, dict):
                    u = uo.get("url")
                    if isinstance(u, str) and u.startswith("data:"):
                        return u
    return None


class OpenRouterImageGenerator(ImageGeneratorBase):
    """
    OpenRouter /v1/chat/completions with modalities + optional image_config.
    No polling — one HTTP round-trip.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        fallback_model: str | None = None,
        timeout: int = 180,
    ):
        self.api_key = api_key
        self.model = model
        self.fallback_model = fallback_model
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )

    def _call(self, model: str, prompt: str, aspect_ratio: str) -> ImageResult:
        modalities = modalities_for_model(model)
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": modalities,
        }
        ic = _normalize_aspect_for_config(aspect_ratio)
        if ic:
            payload["image_config"] = {"aspect_ratio": ic}

        resp = self.session.post(
            OPENROUTER_CHAT_COMPLETIONS_URL,
            json=payload,
            timeout=self.timeout,
        )
        try:
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"Invalid JSON from OpenRouter ({resp.status_code}): {e}") from e

        if resp.status_code >= 400:
            err_msg = "unknown error"
            if isinstance(data, dict) and data.get("error"):
                e = data["error"]
                err_msg = e.get("message", str(e)) if isinstance(e, dict) else str(e)
            raise RuntimeError(f"OpenRouter {resp.status_code}: {err_msg}")

        data_url = extract_image_data_url_from_openrouter_response(data)
        if not data_url:
            raise RuntimeError("OpenRouter returned no image in response (check model and modalities)")

        return ImageResult(
            status="completed",
            provider_task_id="openrouter-sync",
            image_url=data_url,
        )

    def generate_and_wait(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        model: str | None = None,
    ) -> ImageResult:
        use_model = model or self.model
        try:
            return self._call(use_model, prompt, aspect_ratio)
        except Exception as first_err:
            fb = self.fallback_model
            if fb and fb != use_model:
                try:
                    return self._call(fb, prompt, aspect_ratio)
                except Exception as second_err:
                    return ImageResult(
                        status="failed",
                        error=f"{first_err}; fallback failed: {second_err}",
                    )
            return ImageResult(status="failed", error=str(first_err))
