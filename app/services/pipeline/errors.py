class PipelineError(Exception):
    """Base class for pipeline-level failures."""


class LLMError(PipelineError):
    """LLM provider call failed."""


class SerpError(PipelineError):
    """SERP provider call failed."""


class ScrapingError(PipelineError):
    """Competitor scraping failed."""


class ParseError(PipelineError):
    """Structured parsing failed."""


class ValidationError(PipelineError):
    """Validation of step input/output failed."""


class BudgetExceededError(PipelineError):
    """Retry/cost budget was exhausted."""


class StepTimeoutError(PipelineError):
    """Step execution timed out."""
