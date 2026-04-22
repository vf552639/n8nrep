from app.services import _pipeline_legacy as legacy


def setup_vars(ctx):
    return legacy.setup_vars(ctx)


def setup_template_vars(ctx):
    return legacy.setup_template_vars(ctx)


def apply_template_vars(text: str, variables: dict) -> tuple[str, dict]:
    return legacy.apply_template_vars(text, variables)
