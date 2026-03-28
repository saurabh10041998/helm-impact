import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from model import Severity
from model import ImpactKind
from model import FieldChange
from model import ImpactVerdict


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


class TestFieldChange:
    def _make(self, **kwargs):
        defaults = dict(
            resource_kind="Deployment",
            resource_name="my-app",
            field_path="spec.replicas",
            old_value=3,
            new_value=5,
        )
        return FieldChange(**{**defaults, **kwargs})

    def test_basic_construction(self):
        fc = self._make()
        assert fc.resource_kind == "Deployment"
        assert fc.resource_name == "my-app"
        assert fc.field_path == "spec.replicas"
        assert fc.old_value == 3
        assert fc.new_value == 5

    def test_string_values(self):
        fc = self._make(
            field_path="spec.template.spec.containers[*].image",
            old_value="my-app:v1.0.0",
            new_value="my-app:v1.1.0",
        )
        assert fc.old_value == "my-app:v1.0.0"
        assert fc.new_value == "my-app:v1.1.0"

    def test_none_old_value_resource_created(self):
        fc = self._make(field_path="<resource>", old_value=None, new_value="<created>")
        assert fc.old_value is None
        assert fc.new_value == "<created>"

    def test_none_new_value_resource_deleted(self):
        fc = self._make(field_path="<resource>", old_value="<existed>", new_value=None)
        assert fc.old_value == "<existed>"
        assert fc.new_value is None

    def test_dict_values(self):
        fc = self._make(
            field_path="spec.template.spec.containers[*].resources",
            old_value={"limits": {"cpu": "500m", "memory": "256Mi"}},
            new_value={"limits": {"cpu": "1", "memory": "512Mi"}},
        )
        assert fc.old_value == {"limits": {"cpu": "500m", "memory": "256Mi"}}
        assert fc.new_value == {"limits": {"cpu": "1", "memory": "512Mi"}}

    def test_list_values(self):
        fc = self._make(
            field_path="spec.accessModes",
            old_value=["ReadWriteOnce"],
            new_value=["ReadWriteMany"],
        )
        assert fc.old_value == ["ReadWriteOnce"]
        assert fc.new_value == ["ReadWriteMany"]

    def test_boolean_values(self):
        fc = self._make(
            field_path="spec.template.spec.automountServiceAccountToken",
            old_value=True,
            new_value=False,
        )
        assert fc.old_value is True
        assert fc.new_value is False

    def test_pvc_kind(self):
        fc = self._make(
            resource_kind="PersistentVolumeClaim",
            resource_name="my-pvc",
        )
        assert fc.resource_kind == "PersistentVolumeClaim"
        assert fc.resource_name == "my-pvc"

    def test_missing_required_fields_raises(self):
        with pytest.raises(TypeError):
            FieldChange(resource_kind="Deployment", resource_name="app")

    def test_dataclass_equality(self):
        fc1 = self._make()
        fc2 = self._make()
        assert fc1 == fc2

    def test_dataclass_inequality(self):
        fc1 = self._make(old_value=2)
        fc2 = self._make(old_value=3)
        assert fc1 != fc2

    def test_field_path_normalized_wildcard(self):
        fc = self._make(
            field_path="spec.container[*].image",
        )
        assert "[*]" in fc.field_path

    def test_field_path_raw_index(self):
        fc = self._make(
            field_path="spec.containers[0].image",
        )
        assert "[0]" in fc.field_path


class TestImpactVerdict:
    def _make_fc(self):
        return FieldChange(
            resource_kind="Deployment",
            resource_name="my-app",
            field_path="spec.replicas",
            old_value=3,
            new_value=5,
        )

    def _make(self, **kwargs):
        defaults = dict(
            severity=Severity.WARNING,
            kind=ImpactKind.ROLLING_RESTART,
            description="Image changed",
            remediation="Monitor pod readiness",
            field_change=self._make_fc(),
        )
        return ImpactVerdict(**{**defaults, **kwargs})

    def test_basic_construction(self):
        v = self._make()
        assert v.severity == Severity.WARNING
        assert v.kind == ImpactKind.ROLLING_RESTART
        assert v.description == "Image changed"
        assert v.remediation == "Monitor pod readiness"

    def test_field_change_is_attached(self):
        fc = self._make_fc()
        v = self._make(field_change=fc)
        assert v.field_change is fc
        assert v.field_change.resource_kind == "Deployment"

    def test_blocker_severity(self):
        v = self._make(
            severity=Severity.BLOCKER,
            kind=ImpactKind.DATA_LOSS_RISK,
            description="PVC shrink attempted",
            remediation="Revert immediately",
        )
        assert v.severity == Severity.BLOCKER
        assert v.kind == ImpactKind.DATA_LOSS_RISK

    def test_info_severity(self):
        v = self._make(severity=Severity.INFO, kind=ImpactKind.NO_IMPACT)
        assert v.severity == Severity.INFO

    def test_danger_severity(self):
        v = self._make(severity=Severity.DANGER, kind=ImpactKind.DOWNTIME)
        assert v.severity == Severity.DANGER

    def test_no_impact_kind(self):
        v = self._make(severity=Severity.INFO, kind=ImpactKind.NO_IMPACT)
        assert v.kind == ImpactKind.NO_IMPACT

    def test_empty_string_description_allowed(self):
        v = self._make(description="")
        assert v.description == ""

    def test_empty_string_remediation_allowed(self):
        v = self._make(remediation="")
        assert v.remediation == ""

    def test_long_description(self):
        long_desc = "x" * 500
        v = self._make(description=long_desc)
        assert len(v.description) == 500

    def test_missing_required_fields_raises(self):
        with pytest.raises(TypeError):
            ImpactVerdict(severity=Severity.INFO, kind=ImpactKind.NO_IMPACT)

    def test_dataclass_equality(self):
        v1 = self._make()
        v2 = self._make()
        assert v1 == v2

    def test_dataclass_inequality_by_severity(self):
        v1 = self._make(severity=Severity.INFO)
        v2 = self._make(severity=Severity.WARNING)
        assert v1 != v2

    def test_field_change_resource_kind_accessible(self):
        v = self._make()
        assert v.field_change.resource_kind == "Deployment"

    def test_field_change_values_accessible(self):
        v = self._make()
        assert v.field_change.old_value == 3
        assert v.field_change.new_value == 5

    def test_pvc_verdict_with_pvc_field_change(self):
        fc = FieldChange(
            resource_kind="PersistentVolumeClaim",
            resource_name="my-pvc",
            field_path="spec.resources.requests.storage",
            old_value="10Gi",
            new_value="5Gi",
        )
        v = self._make(
            severity=Severity.BLOCKER,
            kind=ImpactKind.DATA_LOSS_RISK,
            description="PVC storage shrink attempted: 10Gi -> 5Gi",
            remediation="PVC shrink is NOT supported - revert this change immediately",
            field_change=fc,
        )
        assert v.field_change.resource_kind == "PersistentVolumeClaim"
        assert v.severity == Severity.BLOCKER
