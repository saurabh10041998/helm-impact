import re

from core.model import FieldChange
from core.model import ImpactVerdict
from core.model import Severity
from core.model import ImpactKind
from core.rules.base import FuncRule


def _path_matches(pattern: str, path: str) -> bool:
    # convert wildcard pattern to regex
    regex_pattern = re.escape(pattern).replace(r"\*", ".*")
    return re.fullmatch(regex_pattern, path) is not None


def _role_rules() -> list[FuncRule]:
    return [
        FuncRule(
            resource_kind="Role",
            name="rules-change",
            matches_fn=lambda c: _path_matches("rules.*", c.field_path),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.WARNING,
                kind=ImpactKind.MANNUAL_INTERVENTION,
                description=f"Role permission rules changed at {c.field_path}",
                remediation=(
                    "The permission surface of this Role changed. Review against the "
                    "principle of least privilege and confirm the new verbs / "
                    "resources / apiGroups are intended."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="Role",
            name="role-fallback",
            matches_fn=lambda c: True,
            verdict_fn=lambda c: _fallback_verdict(c),
        ),
    ]


def _fallback_verdict(c: FieldChange) -> ImpactVerdict:
    return ImpactVerdict(
        severity=Severity.INFO,
        kind=ImpactKind.UNCLEAR,
        description=f"Role change at {c.field_path}",
        remediation="Review Mannually",
        field_change=c,
    )
