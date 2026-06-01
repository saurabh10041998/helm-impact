from typing import Optional

from core.model import ImpactVerdict


def filter_by_resource(
    verdicts: list[ImpactVerdict],
    include: Optional[list[str]] = None,
    exclude: Optional[list[str]] = None,
) -> list[ImpactVerdict]:
    """
    Narrow verdicts down to a set of resources.

    A token matches a verdict when it equals either the resource kind or the
    resource name, so callers can say `Deployment` or `my-app` interchangeably.

    `include` and `exclude` are mutually exclusive; pass at most one. When both
    are empty/None the verdicts are returned unchanged.
    """
    if include:
        wanted = set(include)
        return [v for v in verdicts if _matches(v, wanted)]

    if exclude:
        hidden = set(exclude)
        return [v for v in verdicts if not _matches(v, hidden)]

    return verdicts


def _matches(verdict: ImpactVerdict, tokens: set[str]) -> bool:
    change = verdict.field_change
    return change.resource_kind in tokens or change.resource_name in tokens
