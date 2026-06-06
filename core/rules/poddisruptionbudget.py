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


def _poddisruptionbudget_rules() -> list[FuncRule]:
    return [
        FuncRule(
            resource_kind="PodDisruptionBudget",
            name="min-available-change",
            matches_fn=lambda c: c.field_path == "spec.minAvailable",
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.WARNING,
                kind=ImpactKind.MANNUAL_INTERVENTION,
                description=(
                    f"PDB minAvailable changed from {c.old_value} to {c.new_value}"
                ),
                remediation=(
                    "This affects how many pods must stay available during voluntary "
                    "disruptions (e.g. node drains). Confirm the value matches the "
                    "workload's availability requirements."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="PodDisruptionBudget",
            name="max-unavailable-change",
            matches_fn=lambda c: c.field_path == "spec.maxUnavailable",
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.WARNING,
                kind=ImpactKind.MANNUAL_INTERVENTION,
                description=(
                    f"PDB maxUnavailable changed from {c.old_value} to {c.new_value}"
                ),
                remediation=(
                    "This affects how many pods may be unavailable during voluntary "
                    "disruptions (e.g. node drains). Confirm the value matches the "
                    "workload's availability requirements."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="PodDisruptionBudget",
            name="selector-change",
            matches_fn=lambda c: _path_matches("spec.selector.*", c.field_path),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.DANGER,
                kind=ImpactKind.MANNUAL_INTERVENTION,
                description=f"PDB selector changed at {c.field_path}",
                remediation=(
                    "A changed selector may stop the PDB from protecting the intended "
                    "pods, leaving them exposed to disruption. Verify the selector "
                    "still targets the correct workload."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="PodDisruptionBudget",
            name="poddisruptionbudget-fallback",
            matches_fn=lambda c: True,
            verdict_fn=lambda c: _fallback_verdict(c),
        ),
    ]


def _fallback_verdict(c: FieldChange) -> ImpactVerdict:
    return ImpactVerdict(
        severity=Severity.INFO,
        kind=ImpactKind.UNCLEAR,
        description=f"PodDisruptionBudget change at {c.field_path}",
        remediation="Review Mannually",
        field_change=c,
    )
