import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.model import Severity
from core.model import ImpactKind
from core.model import FieldChange
from core.model import ImpactVerdict
from core.rules.secret import _secret_rules


def make_field_change(**kwargs) -> FieldChange:
    defaults = dict(
        resource_kind="Secret",
        resource_name="my-secret",
        field_path="data.password",
        old_value="b2xk",
        new_value="bmV3",
    )
    return FieldChange(**{**defaults, **kwargs})


def evaluate_one(fc: FieldChange) -> ImpactVerdict | None:
    rules = _secret_rules()
    for rule in rules:
        if rule.matches(fc):
            return rule.verdict(fc)
    return None


def test_secret_rules_returns_non_empty_list():
    rules = _secret_rules()
    assert isinstance(rules, list)
    assert len(rules) > 0


def test_all_rules_have_secret_resource_kind():
    assert all(r.resource_kind == "Secret" for r in _secret_rules())


def test_all_rules_have_name():
    assert all(r.name != "" for r in _secret_rules())


def test_rules_do_not_match_wrong_resource_kind():
    fc = make_field_change(resource_kind="ConfigMap")
    for rule in _secret_rules():
        assert rule.matches(fc) is False


def test_secret_removed_is_data_loss_risk():
    fc = make_field_change(
        field_path="<resource>", old_value="<existed>", new_value=None
    )
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.DANGER
    assert verdict.kind == ImpactKind.DATA_LOSS_RISK


def test_secret_added_is_info():
    fc = make_field_change(
        field_path="<resource>", old_value=None, new_value="<created>"
    )
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.INFO
    assert verdict.kind == ImpactKind.MANNUAL_INTERVENTION


def test_secret_type_change_is_danger():
    fc = make_field_change(
        field_path="type", old_value="Opaque", new_value="kubernetes.io/tls"
    )
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.DANGER
    assert verdict.kind == ImpactKind.MANNUAL_INTERVENTION


def test_secret_data_change_triggers_rolling_restart():
    fc = make_field_change(field_path="data.password")
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.WARNING
    assert verdict.kind == ImpactKind.ROLLING_RESTART


def test_secret_data_change_does_not_leak_values():
    fc = make_field_change(
        field_path="data.password", old_value="SECRET_OLD", new_value="SECRET_NEW"
    )
    verdict = evaluate_one(fc)
    assert "SECRET_OLD" not in verdict.description
    assert "SECRET_NEW" not in verdict.description
    assert "SECRET_OLD" not in verdict.remediation
    assert "SECRET_NEW" not in verdict.remediation


def test_string_data_change_triggers_rolling_restart():
    fc = make_field_change(field_path="stringData.token")
    verdict = evaluate_one(fc)
    assert verdict.kind == ImpactKind.ROLLING_RESTART


def test_unmatched_change_falls_back_to_info():
    fc = make_field_change(field_path="metadata.labels.team")
    verdict = evaluate_one(fc)
    assert verdict is not None
    assert verdict.severity == Severity.INFO
    assert verdict.kind == ImpactKind.UNCLEAR
