from core.model import FieldChange, ImpactVerdict

from typing import Optional, Callable
from abc import ABC, abstractmethod


class Rule(ABC):
    """
    A Single evaluable rule.
    Subclass or use FuncRule for simple cases.
    """

    resource_kind: str

    @abstractmethod
    def matches(self, change: FieldChange) -> bool: ...

    @abstractmethod
    def verdict(self, change: FieldChange) -> ImpactVerdict: ...


class FuncRule(Rule):
    """
    A lightweight rule built from two callables.
    Good for 90% of cases
    """

    def __init__(
        self,
        resource_kind: Optional[str],
        matches_fn: Callable[[FieldChange], bool],
        verdict_fn: Callable[[FieldChange], ImpactVerdict],
        name: str = "",
    ):
        self.resource_kind = resource_kind
        self._matches_fn = matches_fn
        self._verdict_fn = verdict_fn
        self.name = name

    def matches(self, change: FieldChange) -> bool:
        if self.resource_kind and change.resource_kind != self.resource_kind:
            return False
        return self._matches_fn(change)

    def verdict(self, change: FieldChange) -> ImpactVerdict:
        return self._verdict_fn(change)
