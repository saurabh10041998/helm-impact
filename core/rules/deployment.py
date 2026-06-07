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


def _deployment_rules() -> list[FuncRule]:
    return [
        FuncRule(
            resource_kind="Deployment",
            name="selector-change",
            matches_fn=lambda c: _path_matches("spec.selector.*", c.field_path),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.DANGER,
                kind=ImpactKind.MANNUAL_INTERVENTION,
                description=(
                    f"selector changed at {c.field_path}: "
                    f"{c.old_value} -> {c.new_value}"
                ),
                remediation=(
                    "spec.selector is immutable -- the apply will be rejected. "
                    "Delete and recreate the Deployment to change it."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="Deployment",
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
                description=(
                    f"Changing container image from {c.old_value} " f"to {c.new_value}"
                ),
                remediation=(
                    "This will trigger a rolling restart. Ensure that the new "
                    "image is compatible and has been tested."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="Deployment",
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
                description=(
                    f"Container resource {c.field_path.split('.')[-1]} limit "
                    f"changed from {c.old_value} to {c.new_value}"
                ),
                remediation=(
                    "Rolling restart -- ensure new limits are within node capacity"
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="Deployment",
            name="env-change",
            matches_fn=lambda c: _any_path_matches(
                [
                    "spec.template.spec.containers.[*].env.*",
                    "spec.template.spec.containers.[*].envFrom.*",
                    "spec.template.spec.initContainers.[*].env.*",
                    "spec.template.spec.initContainers.[*].envFrom.*",
                ],
                c.field_path,
            ),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.WARNING,
                kind=ImpactKind.ROLLING_RESTART,
                description=(
                    f"Container environment changed at {c.field_path}: "
                    f"{c.old_value} -> {c.new_value}"
                ),
                remediation=(
                    "Env/envFrom change alters the pod template -- this triggers a "
                    "rolling restart. Verify the new configuration is correct."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="Deployment",
            name="probe-change",
            matches_fn=lambda c: _any_path_matches(
                [
                    "spec.template.spec.containers.[*].livenessProbe.*",
                    "spec.template.spec.containers.[*].readinessProbe.*",
                    "spec.template.spec.containers.[*].startupProbe.*",
                ],
                c.field_path,
            ),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.WARNING,
                kind=ImpactKind.ROLLING_RESTART,
                description=(
                    f"Container probe changed at {c.field_path}: "
                    f"{c.old_value} -> {c.new_value}"
                ),
                remediation=(
                    "Probe change triggers a rolling restart and affects rollout "
                    "health gating -- ensure thresholds are appropriate."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="Deployment",
            name="command-args-change",
            matches_fn=lambda c: _any_path_matches(
                [
                    "spec.template.spec.containers.[*].command.*",
                    "spec.template.spec.containers.[*].args.*",
                    "spec.template.spec.initContainers.[*].command.*",
                    "spec.template.spec.initContainers.[*].args.*",
                ],
                c.field_path,
            ),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.WARNING,
                kind=ImpactKind.ROLLING_RESTART,
                description=(
                    f"Container command/args changed at {c.field_path}: "
                    f"{c.old_value} -> {c.new_value}"
                ),
                remediation=(
                    "Entrypoint/args change triggers a rolling restart and may alter "
                    "runtime behaviour -- verify the new invocation is correct."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="Deployment",
            name="volume-change",
            matches_fn=lambda c: _any_path_matches(
                [
                    "spec.template.spec.volumes.*",
                    "spec.template.spec.containers.[*].volumeMounts.*",
                    "spec.template.spec.initContainers.[*].volumeMounts.*",
                ],
                c.field_path,
            ),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.WARNING,
                kind=ImpactKind.ROLLING_RESTART,
                description=(
                    f"Volume configuration changed at {c.field_path}: "
                    f"{c.old_value} -> {c.new_value}"
                ),
                remediation=(
                    "Volume/mount change triggers a rolling restart -- verify data "
                    "paths and that referenced volumes exist."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="Deployment",
            name="port-change",
            matches_fn=lambda c: _path_matches(
                "spec.template.spec.containers.[*].ports.*", c.field_path
            ),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.WARNING,
                kind=ImpactKind.ROLLING_RESTART,
                description=(
                    f"Container port changed at {c.field_path}: "
                    f"{c.old_value} -> {c.new_value}"
                ),
                remediation=(
                    "Container port change triggers a rolling restart -- confirm the "
                    "Service and any network policies still target the right port."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="Deployment",
            name="service-account-change",
            matches_fn=lambda c: c.field_path
            == "spec.template.spec.serviceAccountName",
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.WARNING,
                kind=ImpactKind.ROLLING_RESTART,
                description=(
                    f"serviceAccountName changed from {c.old_value} to {c.new_value}"
                ),
                remediation=(
                    "Service account change alters pod identity/permissions and "
                    "triggers a rolling restart -- verify the new RBAC is correct."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="Deployment",
            name="replicas-change",
            matches_fn=lambda c: c.field_path == "spec.replicas",
            verdict_fn=lambda c: ImpactVerdict(
                severity=(
                    Severity.DANGER if (c.new_value or 0) == 0 else Severity.INFO
                ),
                kind=(
                    ImpactKind.DOWNTIME
                    if (c.new_value or 0) == 0
                    else ImpactKind.SCALE_EVENT
                ),
                description=f"Changing replicas from {c.old_value} to {c.new_value}",
                remediation=(
                    "Scaling to zero removes all pods and causes downtime -- "
                    "confirm the outage is intended."
                    if (c.new_value or 0) == 0
                    else (
                        "Scale down -- ensure traffic can be handled by fewer pods."
                        if (c.new_value or 1) < (c.old_value or 1)
                        else "Scale up -- ensure cluster has capacity for "
                        "additional pods."
                    )
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="Deployment",
            name="strategy-type-change",
            matches_fn=lambda c: c.field_path == "spec.strategy.type",
            verdict_fn=lambda c: ImpactVerdict(
                severity=(
                    Severity.DANGER if c.new_value == "Recreate" else Severity.WARNING
                ),
                kind=(
                    ImpactKind.DOWNTIME
                    if c.new_value == "Recreate"
                    else ImpactKind.ROLLING_RESTART
                ),
                description=(
                    f"Deployment strategy changed from {c.old_value} "
                    f"to {c.new_value}"
                ),
                remediation=(
                    "Recreate strategy will cause downtime -- revert to "
                    "Rollingupdate or ensure downtime is acceptable."
                    if c.new_value == "Recreate"
                    else "Strategy change will trigger a rolling restart -- "
                    "ensure strategy is appropriate"
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="Deployment",
            name="strategy-rolling-params-change",
            matches_fn=lambda c: _any_path_matches(
                [
                    "spec.strategy.rollingUpdate.maxUnavailable",
                    "spec.strategy.rollingUpdate.maxSurge",
                ],
                c.field_path,
            ),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.WARNING,
                kind=ImpactKind.ROLLING_RESTART,
                description=(
                    f"Rollout pacing changed at {c.field_path}: "
                    f"{c.old_value} -> {c.new_value}"
                ),
                remediation=(
                    "maxUnavailable/maxSurge govern rollout pacing -- a higher "
                    "maxUnavailable can reduce capacity mid-rollout. Confirm the "
                    "values are appropriate."
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="Deployment",
            name="fallback",
            matches_fn=lambda c: True,
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.INFO,
                kind=ImpactKind.UNCLEAR,
                description=(
                    f"Unclassified Deployment change at {c.field_path}: "
                    f"{c.old_value} -> {c.new_value}"
                ),
                remediation=(
                    "No specific rule matched -- review this change manually to "
                    "confirm it is safe."
                ),
                field_change=c,
            ),
        ),
    ]
