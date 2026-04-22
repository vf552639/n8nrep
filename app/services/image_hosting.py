"""
Image hosting service — ImgBB implementation.
"""

import base64

import requests


class ImgBBUploader:
    """
    ImgBB API: https://api.imgbb.com/

    POST https://api.imgbb.com/1/upload
    Params:
    - key: IMGBB_API_KEY
    - image: base64-encoded data or URL
    - name: filename (slug)
    - expiration: None (permanent)

    Returns: {"url": "...", "display_url": "...", "delete_url": "..."}
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.upload_url = "https://api.imgbb.com/1/upload"

    def upload_from_bytes(self, image_bytes: bytes, filename: str) -> dict:
        """Upload raw image bytes to ImgBB."""
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        payload = {
            "key": self.api_key,
            "image": image_b64,
            "name": filename,
        }
        upload_resp = requests.post(self.upload_url, data=payload, timeout=30)
        upload_resp.raise_for_status()
        data = upload_resp.json()

        if not data.get("success"):
            raise RuntimeError(f"ImgBB upload failed: {data.get('error', {}).get('message', str(data))}")

        img_data = data.get("data", {})
        return {
            "url": img_data.get("url", ""),
            "display_url": img_data.get("display_url", ""),
            "delete_url": img_data.get("delete_url", ""),
        }

    def upload_from_data_url(self, data_url: str, filename: str) -> dict:
        """Parse `data:image/...;base64,...` from OpenRouter and upload."""
        if not isinstance(data_url, str) or not data_url.startswith("data:"):
            raise ValueError("Expected a base64 data URL")
        comma = data_url.find(",")
        if comma == -1:
            raise ValueError("Invalid data URL: no comma")
        b64 = data_url[comma + 1 :].strip()
        raw = base64.b64decode(b64)
        return self.upload_from_bytes(raw, filename)

    def upload_from_url(self, image_url: str, filename: str) -> dict:
        """
        Downloads image from URL, uploads to ImgBB.
        Returns: {"url": "...", "display_url": "...", "delete_url": "..."}
        """
        resp = requests.get(image_url, timeout=60)
        resp.raise_for_status()
        return self.upload_from_bytes(resp.content, filename)
