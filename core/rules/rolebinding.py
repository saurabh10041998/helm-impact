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


def _rolebinding_rules() -> list[FuncRule]:
    return [
        FuncRule(
            resource_kind="RoleBinding",
            name="roleref-change",
            matches_fn=lambda c: _path_matches("roleRef.*", c.field_path),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.DANGER,
                kind=ImpactKind.MANNUAL_INTERVENTION,
                description=f"RoleBinding roleRef changed at {c.field_path}",
                remediation=(
                    "roleRef is immutable on a live RoleBinding -- this requires "
                    "deleting and recreating the binding. Plan for the recreation to "
                    "avoid a window where access is lost."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="RoleBinding",
            name="subjects-change",
            matches_fn=lambda c: _path_matches("subjects.*", c.field_path),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.WARNING,
                kind=ImpactKind.MANNUAL_INTERVENTION,
                description=f"RoleBinding subjects changed at {c.field_path}",
                remediation=(
                    "The set of principals granted this Role changed. Confirm who "
                    "gains or loses access is intended."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="RoleBinding",
            name="rolebinding-fallback",
            matches_fn=lambda c: True,
            verdict_fn=lambda c: _fallback_verdict(c),
        ),
    ]


def _fallback_verdict(c: FieldChange) -> ImpactVerdict:
    return ImpactVerdict(
        severity=Severity.INFO,
        kind=ImpactKind.UNCLEAR,
        description=f"RoleBinding change at {c.field_path}",
        remediation="Review Mannually",
        field_change=c,
    )
