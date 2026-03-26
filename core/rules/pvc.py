from core.model import FieldChange
from core.model import ImpactVerdict
from core.model import Severity
from core.model import ImpactKind
from core.rules.base import FuncRule


def _parse_storage(val: str) -> float:
    units = {
        "Ki": 1024,
        "Mi": 1024**2,
        "Gi": 1024**3,
        "Ti": 1024**4,
    }
    for suffix, multiplier in units.items():
        if val.endswith(suffix):
            return float(val[: -len(suffix)]) * multiplier
    return float(val)  # assume it's in bytes if no suffix


def _pvc_rules() -> list[FuncRule]:
    return [
        FuncRule(
            resource_kind="PersistentVolumeClaim",
            name="storage-size-change",
            matches_fn=lambda c: c.field_path == "spec.resources.requests.storage",
            verdict_fn=lambda c: _storage_verdict(c),
        )
    ]


def _storage_verdict(c: FieldChange) -> ImpactVerdict:
    try:
        old_size = _parse_storage(c.old_value or "0")
        new_size = _parse_storage(c.new_value or "0")
        is_expansion = new_size > old_size

    except ValueError:
        is_expansion = False

    if is_expansion:
        return ImpactVerdict(
            severity=Severity.BLOCKER,
            kind=ImpactKind.MANNUAL_INTERVENTION,
            description=f"Expanding PVC storage from {c.old_value} to {c.new_value}",
            remediation=(
                "PVC expansion may require manual intervention and can lead to downtime. "
                "Ensure that the underlying storage class supports expansion and that the "
                "application can handle the increased storage size without issues."
            ),
            field_change=c,
        )
    return ImpactVerdict(
        severity=Severity.BLOCKER,
        kind=ImpactKind.DATA_LOSS_RISK,
        description=f"PVC shrink attempted: {c.old_value} -> {c.new_value}",
        remediation=(
            "Shrinking PVC storage is NOT supported"
            "-- revert this change immediately to avoid data loss."
        ),
        field_change=c,
    )
