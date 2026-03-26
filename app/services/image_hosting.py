"""
Image hosting service — ImgBB implementation.
"""

import base64
import requests
from typing import Optional


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

    def upload_from_url(self, image_url: str, filename: str) -> dict:
        """
        Downloads image from URL, uploads to ImgBB.
        Returns: {"url": "...", "display_url": "...", "delete_url": "..."}
        """
        # Download the image
        resp = requests.get(image_url, timeout=60)
        resp.raise_for_status()

        image_b64 = base64.b64encode(resp.content).decode("utf-8")

        # Upload to ImgBB
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
