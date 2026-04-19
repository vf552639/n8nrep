from typing import Literal

from pydantic import BaseModel, ValidationInfo, field_validator


class SerpConfig(BaseModel):
    search_engine: Literal["google", "bing", "google+bing"] = "google"
    depth: Literal[10, 20, 30, 50, 100] = 10
    device: Literal["mobile", "desktop"] = "mobile"
    os: Literal["android", "ios", "windows", "macos"] = "android"

    @field_validator("os")
    @classmethod
    def validate_os_device_combo(cls, v: str, info: ValidationInfo) -> str:
        data = info.data or {}
        device = data.get("device", "mobile")
        if device == "mobile" and v not in ("android", "ios"):
            raise ValueError(f"Mobile device supports only android/ios, got {v}")
        if device == "desktop" and v not in ("windows", "macos"):
            raise ValueError(f"Desktop device supports only windows/macos, got {v}")
        return v
