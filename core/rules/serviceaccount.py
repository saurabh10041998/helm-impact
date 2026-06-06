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


def _serviceaccount_rules() -> list[FuncRule]:
    return [
        FuncRule(
            resource_kind="ServiceAccount",
            name="automount-token-change",
            matches_fn=lambda c: c.field_path == "automountServiceAccountToken",
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.WARNING,
                kind=ImpactKind.MANNUAL_INTERVENTION,
                description=(
                    f"automountServiceAccountToken changed from {c.old_value} "
                    f"to {c.new_value}"
                ),
                remediation=(
                    "Toggling token automounting can break pods that rely on the "
                    "API token or unexpectedly expose credentials. Verify the "
                    "consuming workloads before applying."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="ServiceAccount",
            name="image-pull-secrets-change",
            matches_fn=lambda c: _path_matches("imagePullSecrets.*", c.field_path),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.WARNING,
                kind=ImpactKind.ROLLING_RESTART,
                description=f"imagePullSecrets changed at {c.field_path}",
                remediation=(
                    "Image pulls may fail until pods using this ServiceAccount are "
                    "restarted. Ensure the referenced pull secret(s) exist."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="ServiceAccount",
            name="iam-annotation-change",
            matches_fn=lambda c: _path_matches("metadata.annotations.*", c.field_path),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.WARNING,
                kind=ImpactKind.MANNUAL_INTERVENTION,
                description=f"ServiceAccount annotation changed at {c.field_path}",
                remediation=(
                    "Cloud identity bindings (IRSA / workload identity) are commonly "
                    "configured via annotations. Verify the new value before applying."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="ServiceAccount",
            name="serviceaccount-fallback",
            matches_fn=lambda c: True,
            verdict_fn=lambda c: _fallback_verdict(c),
        ),
    ]


def _fallback_verdict(c: FieldChange) -> ImpactVerdict:
    return ImpactVerdict(
        severity=Severity.INFO,
        kind=ImpactKind.UNCLEAR,
        description=f"ServiceAccount change at {c.field_path}",
        remediation="Review Mannually",
        field_change=c,
    )
