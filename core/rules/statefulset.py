import re
from core.model import ImpactVerdict
from core.model import Severity
from core.model import ImpactKind
from core.rules.base import FuncRule


def _path_matches(pattern: str, path: str) -> bool:
    # convert wildcard pattern to regex
    regex_pattern = re.escape(pattern).replace(r"\*", ".*")
    return re.fullmatch(regex_pattern, path) is not None


def _statefulset_rules() -> list[FuncRule]:
    return [
        FuncRule(
            resource_kind="StatefulSet",
            name="image-change",
            matches_fn=lambda c: _path_matches(
                "spec.template.spec.containers.[*].image", c.field_path
            ),
            verdict_fn=lambda c: ImpactVerdict(
                severity=Severity.INFO,
                kind=ImpactKind.ROLLING_RESTART,
                description=f"Changing container image from {c.old_value} to {c.new_value}t",
                remediation=(
                    "This will trigger a rolling restart of the statefulset. Ensure that the new image is compatible and has been tested."
                ),
                field_change=c,
            ),
        )
    ]
