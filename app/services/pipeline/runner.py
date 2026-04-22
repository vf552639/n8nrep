from app.services import _pipeline_legacy as legacy


def run_phase(*args, **kwargs):
    return legacy.run_phase(*args, **kwargs)


def run_pipeline(*args, **kwargs):
    return legacy.run_pipeline(*args, **kwargs)
