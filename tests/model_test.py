import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from model import Severity
from model import ImpactKind


class TestSeverityEnum:
    def test_all_values_exist(self):
        assert Severity.INFO.value == "info"
        assert Severity.WARNING.value == "warning"
        assert Severity.DANGER.value == "danger"
        assert Severity.BLOCKER.value == "blocker"

    def test_count(self):
        assert len(Severity) == 4

    def test_from_value(self):
        assert Severity("info") == Severity.INFO
        assert Severity("warning") == Severity.WARNING
        assert Severity("danger") == Severity.DANGER
        assert Severity("blocker") == Severity.BLOCKER

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            Severity("critical")


class TestImpactKindEnum:
    def test_all_values_exist(self):
        assert ImpactKind.ROLLING_RESTART.value == "rolling_restart"
        assert ImpactKind.DOWNTIME.value == "downtime"
        assert ImpactKind.DATA_LOSS_RISK.value == "data_loss_risk"
        assert ImpactKind.MANNUAL_INTERVENTION.value == "manual_intervention"
        assert ImpactKind.SCALE_EVENT.value == "scale_event"
        assert ImpactKind.NO_IMPACT.value == "no_impact"
        assert ImpactKind.UNCLEAR.value == "unclear"

    def test_count(self):
        assert len(ImpactKind) == 7

    def test_from_value(self):
        assert ImpactKind("rolling_restart") == ImpactKind.ROLLING_RESTART
        assert ImpactKind("downtime") == ImpactKind.DOWNTIME
        assert ImpactKind("data_loss_risk") == ImpactKind.DATA_LOSS_RISK
        assert ImpactKind("manual_intervention") == ImpactKind.MANNUAL_INTERVENTION
        assert ImpactKind("scale_event") == ImpactKind.SCALE_EVENT
        assert ImpactKind("no_impact") == ImpactKind.NO_IMPACT
        assert ImpactKind("unclear") == ImpactKind.UNCLEAR

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            ImpactKind("performance_degradation")
