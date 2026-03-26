"""
Image generation service — GoAPI (Midjourney proxy) implementation.
"""

import time
import requests
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ImageResult:
    status: str  # "pending" | "processing" | "completed" | "failed"
    provider_task_id: str = ""
    image_url: Optional[str] = None   # URL from Midjourney/GoAPI
    hosted_url: Optional[str] = None  # URL after upload to ImgBB
    error: Optional[str] = None


class ImageGeneratorBase(ABC):
    @abstractmethod
    def generate(self, prompt: str, aspect_ratio: str = "16:9") -> str:
        """Submit a prompt, return provider task_id."""
        pass

    @abstractmethod
    def get_status(self, task_id: str) -> ImageResult:
        """Check generation status."""
        pass

    @abstractmethod
    def generate_and_wait(self, prompt: str, aspect_ratio: str = "16:9") -> ImageResult:
        """Submit a prompt and poll until result or timeout."""
        pass


class GoApiMidjourneyGenerator(ImageGeneratorBase):
    """
    GoAPI.ai — REST API proxy for Midjourney.
    Docs: https://docs.goapi.ai/midjourney

    Flow:
    1. POST /mj/v2/imagine → get task_id
    2. Poll GET /mj/v2/fetch/{task_id} every N seconds
    3. When status == "finished" → grab image_url
    """

    def __init__(self, api_key: str, base_url: str = "https://api.goapi.ai",
                 poll_interval: int = 10, poll_timeout: int = 300):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.poll_interval = poll_interval
        self.poll_timeout = poll_timeout
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        })

    def generate(self, prompt: str, aspect_ratio: str = "16:9") -> str:
        """POST /mj/v2/imagine — returns task_id."""
        # Ensure aspect ratio is in the prompt
        if "--ar" not in prompt:
            prompt = f"{prompt} --ar {aspect_ratio}"
        if "--v" not in prompt:
            prompt = f"{prompt} --v 6.1"

        url = f"{self.base_url}/mj/v2/imagine"
        payload = {
            "prompt": prompt,
            "process_mode": "fast",
        }

        resp = self.session.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 200 and data.get("code") != "success":
            error_msg = data.get("message") or data.get("error") or str(data)
            raise RuntimeError(f"GoAPI imagine failed: {error_msg}")

        task_id = data.get("data", {}).get("task_id") or data.get("data", {}).get("id") or ""
        if not task_id:
            raise RuntimeError(f"GoAPI returned no task_id: {data}")

        return task_id

    def get_status(self, task_id: str) -> ImageResult:
        """GET /mj/v2/fetch/{task_id} — returns ImageResult."""
        url = f"{self.base_url}/mj/v2/fetch"
        payload = {"task_id": task_id}

        resp = self.session.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        raw_status = (data.get("data", {}).get("status") or "").lower()
        image_url = data.get("data", {}).get("image_url") or data.get("data", {}).get("task_result", {}).get("image_url")

        if raw_status in ("finished", "completed"):
            return ImageResult(
                status="completed",
                provider_task_id=task_id,
                image_url=image_url,
            )
        elif raw_status in ("failed", "error", "banned"):
            return ImageResult(
                status="failed",
                provider_task_id=task_id,
                error=data.get("data", {}).get("error_message") or data.get("message") or raw_status,
            )
        else:
            return ImageResult(
                status="pending" if raw_status in ("pending", "submitted", "queued") else "processing",
                provider_task_id=task_id,
            )

    def generate_and_wait(self, prompt: str, aspect_ratio: str = "16:9") -> ImageResult:
        """Submit prompt, poll until complete/failed/timeout."""
        task_id = self.generate(prompt, aspect_ratio)
        elapsed = 0

        while elapsed < self.poll_timeout:
            time.sleep(self.poll_interval)
            elapsed += self.poll_interval

            result = self.get_status(task_id)
            if result.status in ("completed", "failed"):
                return result

        return ImageResult(
            status="failed",
            provider_task_id=task_id,
            error=f"Timeout after {self.poll_timeout}s",
        )
