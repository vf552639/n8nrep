from app.services import _pipeline_legacy as legacy


def pick_structured_html_for_assembly(ctx):
    return legacy.pick_structured_html_for_assembly(ctx)


def pick_html_for_meta(ctx):
    return legacy.pick_html_for_meta(ctx)
