from fastapi import APIRouter

from app.schemas.auth import LoginStartResponse, LoginStatus, LogoutResponse
from app.services.auth import codex_oauth

router = APIRouter()


@router.get("/status", response_model=LoginStatus)
def status() -> LoginStatus:
    return LoginStatus(**codex_oauth.read_status())


@router.post("/login", response_model=LoginStartResponse)
def login() -> LoginStartResponse:
    """Returns instructions for the Electron renderer to drive the login flow.

    We do not perform OAuth ourselves; we depend on the user's `codex` CLI to
    write ~/.codex/auth.json. Electron's IPC handler will spawn the CLI.
    """
    return LoginStartResponse(
        method="cli",
        cli_command=["codex", "login"],
        notice=(
            "Click Login to launch `codex login` in a terminal child process. "
            "After completion, this status endpoint will show 'logged_in: true'."
        ),
    )


@router.post("/logout", response_model=LogoutResponse)
def logout() -> LogoutResponse:
    codex_oauth.logout()
    return LogoutResponse(logged_out=True)
