from pydantic import BaseModel


class LoginStatus(BaseModel):
    logged_in: bool
    method: str | None = None
    account_id: str | None = None


class LogoutResponse(BaseModel):
    logged_out: bool


class LoginStartResponse(BaseModel):
    """Returned by /login — Electron uses this to open a child window or spawn the CLI."""

    method: str  # "cli" | "browser"
    url: str | None = None
    cli_command: list[str] | None = None  # e.g., ["codex", "login"]
    notice: str
