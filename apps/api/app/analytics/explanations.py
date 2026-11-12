"""Extension boundary for future optional explanation providers.

The working application uses deterministic engine explanations exclusively.
Any external provider must accept computed metrics only, validate numeric claims,
cache by model version + metrics hash, and fall back to deterministic templates.
"""

from typing import Any, Protocol


class ExplanationProvider(Protocol):
    async def explain(self, computed_metrics: dict[str, Any]) -> list[str]:
        """Return validated explanations; implementations must not discover statistics."""
        ...
