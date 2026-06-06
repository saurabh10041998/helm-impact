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


def _any_path_matches(patterns: list[str], path: str) -> bool:
    return any(_path_matches(p, path) for p in patterns)


def _secret_rules() -> list[FuncRule]:
    return [
        FuncRule(
            resource_kind="Secret",
            name="secret-removed",
            matches_fn=lambda c: c.field_path == "<resource>" and c.new_value is None,
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.DANGER,
                kind=ImpactKind.DATA_LOSS_RISK,
                description=f"Secret {c.resource_name} removed",
                remediation=(
                    "Workloads mounting or referencing this Secret may fail to start "
                    "or lose access. Confirm no running workloads depend on it."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="Secret",
            name="secret-added",
            matches_fn=lambda c: (
                c.field_path == "<resource>" and c.new_value == "<created>"
            ),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.INFO,
                kind=ImpactKind.MANNUAL_INTERVENTION,
                description=f"Secret {c.resource_name} added",
                remediation=(
                    "A new Secret is introduced. Verify its contents are correct and "
                    "that consuming workloads reference it as expected."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="Secret",
            name="secret-type-change",
            matches_fn=lambda c: c.field_path == "type",
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.DANGER,
                kind=ImpactKind.MANNUAL_INTERVENTION,
                description=f"Secret type changed from {c.old_value} to {c.new_value}",
                remediation=(
                    "A Secret's type is immutable on a live object -- this requires "
                    "deleting and recreating the Secret. Plan for the recreation and "
                    "any dependent workload restarts."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="Secret",
            name="secret-data-change",
            # NOTE: never include old_value/new_value here -- secret data must
            # not be printed. Report only the key path that changed.
            matches_fn=lambda c: _any_path_matches(
                [
                    "data.*",
                    "stringData.*",
                ],
                c.field_path,
            ),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.WARNING,
                kind=ImpactKind.ROLLING_RESTART,
                description=f"Secret data changed at key '{c.field_path}'",
                remediation=(
                    "Pods consuming this Secret as env vars or mounted files need a "
                    "rolling restart to pick up the new value. (Secret values are "
                    "intentionally not displayed.)"
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="Secret",
            name="secret-fallback",
            matches_fn=lambda c: True,
            verdict_fn=lambda c: _fallback_verdict(c),
        ),
    ]


def _fallback_verdict(c: FieldChange) -> ImpactVerdict:
    return ImpactVerdict(
        severity=Severity.INFO,
        kind=ImpactKind.UNCLEAR,
        description=f"Secret change at {c.field_path}",
        remediation="Review Mannually",
        field_change=c,
    )
