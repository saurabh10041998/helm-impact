import re

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


def _statefulset_rules() -> list[FuncRule]:
    return [
        FuncRule(
            resource_kind="StatefulSet",
            name="image-change",
            matches_fn=lambda c: _any_path_matches(
                [
                    "spec.template.spec.containers.[*].image",
                    "spec.template.spec.initContainers.[*].image",
                ],
                c.field_path,
            ),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.WARNING,
                kind=ImpactKind.ROLLING_RESTART,
                description=f"Changing container image from {c.old_value} to {c.new_value}",
                remediation=(
                    "This will trigger a rolling restart of the statefulset (governed "
                    "by updateStrategy). Ensure the new image is compatible and tested."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="StatefulSet",
            name="volume-claim-template-change",
            matches_fn=lambda c: _path_matches(
                "spec.volumeClaimTemplates.*", c.field_path
            ),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.DANGER,
                kind=ImpactKind.DATA_LOSS_RISK,
                description=(
                    f"volumeClaimTemplates changed at {c.field_path}: "
                    f"{c.old_value} -> {c.new_value}"
                ),
                remediation=(
                    "volumeClaimTemplates is immutable -- the change is ignored on "
                    "existing PVCs and recreating the StatefulSet can drop data. "
                    "Handle PVCs manually (e.g. delete StatefulSet with "
                    "--cascade=orphan, then resize/recreate PVCs deliberately)."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="StatefulSet",
            name="service-name-change",
            matches_fn=lambda c: c.field_path == "spec.serviceName",
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.DANGER,
                kind=ImpactKind.MANNUAL_INTERVENTION,
                description=f"serviceName changed from {c.old_value} to {c.new_value}",
                remediation=(
                    "spec.serviceName is immutable -- the apply will be rejected. "
                    "Delete and recreate the StatefulSet to change it."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="StatefulSet",
            name="selector-change",
            matches_fn=lambda c: _path_matches("spec.selector.*", c.field_path),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.DANGER,
                kind=ImpactKind.MANNUAL_INTERVENTION,
                description=f"selector changed at {c.field_path}: {c.old_value} -> {c.new_value}",
                remediation=(
                    "spec.selector is immutable -- the apply will be rejected. "
                    "Delete and recreate the StatefulSet to change it."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="StatefulSet",
            name="pod-management-policy-change",
            matches_fn=lambda c: c.field_path == "spec.podManagementPolicy",
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.DANGER,
                kind=ImpactKind.MANNUAL_INTERVENTION,
                description=(
                    f"podManagementPolicy changed from {c.old_value} to {c.new_value}"
                ),
                remediation=(
                    "spec.podManagementPolicy is immutable post-creation -- the apply "
                    "will be rejected. Delete and recreate the StatefulSet to change it."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="StatefulSet",
            name="update-strategy-change",
            matches_fn=lambda c: c.field_path == "spec.updateStrategy.type",
            verdict_fn=lambda c: ImpactVerdict(
                severity=(
                    Severity.DANGER if c.new_value == "OnDelete" else Severity.WARNING
                ),
                kind=(
                    ImpactKind.MANNUAL_INTERVENTION
                    if c.new_value == "OnDelete"
                    else ImpactKind.ROLLING_RESTART
                ),
                description=(
                    f"updateStrategy changed from {c.old_value} to {c.new_value}"
                ),
                remediation=(
                    "OnDelete means pods will NOT auto-update -- you must manually "
                    "delete pods to roll out template changes."
                    if c.new_value == "OnDelete"
                    else "RollingUpdate will trigger a rolling restart on template "
                    "changes -- ensure the strategy is appropriate."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="StatefulSet",
            name="replicas-change",
            matches_fn=lambda c: c.field_path == "spec.replicas",
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.INFO,
                kind=ImpactKind.SCALE_EVENT,
                description=f"Changing replicas from {c.old_value} to {c.new_value}",
                remediation=(
                    "Scale down -- StatefulSet terminates highest-ordinal pods first; "
                    "ensure traffic can be handled by fewer pods."
                    if (c.new_value or 1) < (c.old_value or 1)
                    else "Scale up -- ensure cluster has capacity for additional pods."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="StatefulSet",
            name="resource-limit-change",
            matches_fn=lambda c: _any_path_matches(
                [
                    "spec.template.spec.containers.[*].resources.limits.*",
                    "spec.template.spec.containers.[*].resources.requests.*",
                    "spec.template.spec.initContainers.[*].resources.limits.*",
                    "spec.template.spec.initContainers.[*].resources.requests.*",
                ],
                c.field_path,
            ),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.WARNING,
                kind=ImpactKind.ROLLING_RESTART,
                description=f"Container resource {c.field_path.split('.')[-1]} limit changed from {c.old_value} to {c.new_value}",
                remediation=(
                    "Rolling restart -- ensure new limits are within node capacity."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="StatefulSet",
            name="fallback",
            matches_fn=lambda c: True,
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.INFO,
                kind=ImpactKind.UNCLEAR,
                description=f"Unclassified StatefulSet change at {c.field_path}: {c.old_value} -> {c.new_value}",
                remediation=(
                    "No specific rule matched -- review this change manually to "
                    "confirm it is safe."
                ),
                field_change=c,
            ),
        ),
    ]
