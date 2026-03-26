import re

from core.model import ImpactVerdict
from core.model import Severity
from core.model import ImpactKind
from core.model import ImpactKind

from core.rules.base import FuncRule


def _path_matches(pattern: str, path: str) -> bool:
    # convert wildcard pattern to regex
    regex_pattern = re.escape(pattern).replace(r"\*", ".*")
    return re.fullmatch(regex_pattern, path) is not None


def _deployment_rules() -> list[FuncRule]:
    return [
        FuncRule(
            resource_kind="Deployment",
            name="image-change",
            matches_fn=lambda c: _path_matches(
                "spec.template.spec.containers.[*].image", c.field_path
            ),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.WARNING,
                kind=ImpactKind.ROLLING_RESTART,
                description=f"Changing container image from {c.old_value} to {c.new_value}t",
                remediation="This will trigger a rolling restart. Ensure that the new image is compatible and has been tested.",
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="Deployment",
            name="replicas-change",
            matches_fn=lambda c: c.field_path == "spec.replicas",
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.INFO,
                kind=ImpactKind.SCALE_EVENT,
                description=f"Changing replicas from {c.old_value} to {c.new_value}",
                remediation=(
                    "Scale down -- ensure traffic can be handled by fewer pods."
                    if (c.new_value or 1) < (c.old_value or 1)
                    else "Scale up -- ensure cluster has capacity for additional pods."
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
                description=f"Deployment strategy changed from {c.old_value} to {c.new_value}",
                remediation=(
                    "Recreate strategy will cause downtime -- revert to Rollingupdate or ensure downtime is acceptable."
                    if c.new_value == "Recreate"
                    else "Strategy change will trigger a rolling restart -- ensure strategy is appropriate"
                ),
                field_change=c,
            ),
        ),
        FuncRule(
            resource_kind="Deployment",
            name="resource-limit-change",
            matches_fn=lambda c: _path_matches(
                "spec.template.spec.containers.[*].resources.limits.*", c.field_path
            ),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.WARNING,
                kind=ImpactKind.ROLLING_RESTART,
                description=f"Container resource {c.field_path.split('.')[-1]} limit changed from {c.old_value} to {c.new_value}",
                remediation=(
                    "Rolling restart -- ensure new limits are within node capacity"
                ),
                field_change=c,
            ),
        ),
    ]
