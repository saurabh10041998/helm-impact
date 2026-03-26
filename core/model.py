from dataclasses import dataclass
from enum import Enum
from typing import Any


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"
    BLOCKER = "blocker"


class ImpactKind(Enum):
    ROLLING_RESTART = "rolling_restart"
    DOWNTIME = "downtime"
    DATA_LOSS_RISK = "data_loss_risk"
    MANNUAL_INTERVENTION = "manual_intervention"
    SCALE_EVENT = "scale_event"
    NO_IMPACT = "no_impact"
    UNCLEAR = "unclear"


@dataclass
class FieldChange:
    resource_kind: str
    resource_name: str
    field_path: str
    old_value: Any
    new_value: Any


@dataclass
class ImpactVerdict:
    severity: Severity
    kind: ImpactKind
    description: str
    remediation: str
    field_change: FieldChange
