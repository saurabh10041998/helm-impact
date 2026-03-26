from core.model import FieldChange
from core.model import ImpactVerdict
from core.model import Severity
from core.model import ImpactKind
from core.rules.base import Rule


class RuleEngine:
    def __init__(self, rules):
        self.rules = []

    def register(self, rule: Rule) -> None:
        self._rules.append(rule)

    def evaluate(self, change: FieldChange) -> ImpactVerdict:
        for rule in self._rules:
            if rule.matches(change):
                return rule.verdict(change)

        # default verdict if no rule matches
        return ImpactVerdict(
            severity=Severity.WARNING,
            kind=ImpactKind.UNCLEAR,
            description=f"No rule matched for {change.resource_kind} {change.field_path}",
            remediation="Review Mannually",
            field_change=change,
        )

    def evaluate_all(self, changes: list[FieldChange]) -> list[ImpactVerdict]:
        return [self.evaluate(change) for change in changes]
