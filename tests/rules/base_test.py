import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.model import Severity
from core.model import ImpactKind
from core.model import FieldChange
from core.model import ImpactVerdict

from core.rules.base import Rule
from core.rules.base import FuncRule


def make_field_change(**kwargs) -> FieldChange:
    defaults = dict(
        resource_kind="Deployment",
        resource_name="my-app",
        field_path="spec.replicas",
        old_value=2,
        new_value=5,
    )
    return FieldChange(**{**defaults, **kwargs})


def make_verdict(fc: FieldChange, **kwargs) -> ImpactVerdict:
    defaults = dict(
        severity=Severity.WARNING,
        kind=ImpactKind.ROLLING_RESTART,
        description="test verdict",
        remediation="do something",
        field_change=fc,
    )
    return ImpactVerdict(**{**defaults, **kwargs})


def alway_match(_fc: FieldChange) -> bool:
    return True


def never_match(_fc: FieldChange) -> bool:
    return False


def simple_verdict(fc: FieldChange) -> ImpactVerdict:
    return make_verdict(fc)


def test_rule_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        Rule()


def test_rule_subclass_without_matches_raises():
    class InCompleteRule(Rule):
        def verdict(self, change: FieldChange) -> ImpactVerdict:
            return make_verdict(change)

    with pytest.raises(TypeError):
        InCompleteRule()


def test_rule_subclass_without_verdict_raises():
    class InCompleteRule(Rule):
        def matches(self, change: FieldChange) -> bool:
            return True

    with pytest.raises(TypeError):
        InCompleteRule()


def test_rule_subclass_with_both_methods_instatiates():
    class ConcreteRule(Rule):
        def matches(self, change: FieldChange) -> bool:
            return True

        def verdict(self, change: FieldChange) -> ImpactVerdict:
            return make_verdict(change)

    rule = ConcreteRule()
    assert rule is not None


def test_rule_subclass_matches_returns_correct_value():
    class ConcreteRule(Rule):
        def matches(self, change: FieldChange) -> bool:
            return change.field_path == "spec.replicas"

        def verdict(self, change: FieldChange) -> ImpactVerdict:
            return make_verdict(change)

    rule = ConcreteRule()
    assert rule.matches(make_field_change(field_path="spec.replicas")) == True
    assert rule.matches(make_field_change(field_path="spec.image")) == False


def test_rule_subclass_verdict_returns_impact_verdict():
    class ConcreteRule(Rule):
        def matches(self, change: FieldChange) -> bool:
            return True

        def verdict(self, change: FieldChange) -> ImpactVerdict:
            return make_verdict(change, severity=Severity.DANGER)

    rule = ConcreteRule()
    verdict = rule.verdict(make_field_change())
    assert isinstance(verdict, ImpactVerdict)
    assert verdict.severity == Severity.DANGER


def test_rule_default_resource_kind_is_none():
    class ConcreteRule(Rule):
        def matches(self, change: FieldChange) -> bool:
            return True

        def verdict(self, change: FieldChange) -> ImpactVerdict:
            return make_verdict(change)

    rule = ConcreteRule()
    assert rule.resource_kind is None


def test_rule_subclass_can_set_resource_kind():
    class DeploymentRule(Rule):
        resource_kind = "Deployment"

        def matches(self, change: FieldChange) -> bool:
            return change.resource_kind == self.resource_kind

        def verdict(self, change: FieldChange) -> ImpactVerdict:
            return make_verdict(change)

    rule = DeploymentRule()
    assert rule.resource_kind == "Deployment"


def test_funcrule_basic_creation():
    rule = FuncRule(
        resource_kind="Deployment",
        matches_fn=alway_match,
        verdict_fn=simple_verdict,
        name="test-rule",
    )
    assert rule.resource_kind == "Deployment"
    assert rule.name == "test-rule"


def test_funcrule_none_resource_kind():
    rule = FuncRule(
        resource_kind=None,
        matches_fn=alway_match,
        verdict_fn=simple_verdict,
    )
    assert rule.resource_kind is None


def test_funcrule_default_name_is_empty_string():
    rule = FuncRule(
        resource_kind=None,
        matches_fn=alway_match,
        verdict_fn=simple_verdict,
    )
    assert rule.name == ""


def test_funcrule_missing_matches_fn_raises():
    with pytest.raises(TypeError):
        FuncRule(
            resource_kind=None,
            verdict_fn=simple_verdict,
        )


def test_funcrule_missing_verdict_fn_raises():
    with pytest.raises(TypeError):
        FuncRule(
            resource_kind=None,
            matches_fn=alway_match,
        )


def test_funcrule_matches_correct_resource_kind():
    rule = FuncRule(
        resource_kind="Deployment",
        matches_fn=alway_match,
        verdict_fn=simple_verdict,
    )
    assert rule.matches(make_field_change(resource_kind="Deployment")) == True
    assert rule.matches(make_field_change(resource_kind="Service")) == False


def test_funcrule_none_resource_kind_mactches_any_kind():
    rule = FuncRule(
        resource_kind=None,
        matches_fn=alway_match,
        verdict_fn=simple_verdict,
    )
    assert rule.matches(make_field_change(resource_kind="Deployment")) == True
    assert rule.matches(make_field_change(resource_kind="Service")) == True
    assert rule.matches(make_field_change(resource_kind="ConfigMap")) == True


def test_funcrule_resource_kind_check_is_case_sensitive():
    rule = FuncRule(
        resource_kind="Deployment",
        matches_fn=alway_match,
        verdict_fn=simple_verdict,
    )
    assert rule.matches(make_field_change(resource_kind="deployment")) == False
    assert rule.matches(make_field_change(resource_kind="DEPLOYMENT")) == False


def test_funcrule_matches_fn_returning_false_does_not_match():
    rule = FuncRule(
        resource_kind=None,
        matches_fn=never_match,
        verdict_fn=simple_verdict,
    )
    assert rule.matches(make_field_change()) == False


def test_funcrule_resource_kind_mismatch_short_circuits_matches_fn():
    called = []

    def tracking_match(change: FieldChange) -> bool:
        called.append(True)
        return True

    rule = FuncRule(
        resource_kind="Deployment",
        matches_fn=tracking_match,
        verdict_fn=simple_verdict,
    )
    assert rule.matches(make_field_change(resource_kind="Service")) == False
    assert called == []


def test_funcrule_matches_fn_received_field_change():
    received = []

    def tracking_match(change: FieldChange) -> bool:
        received.append(change)
        return True

    rule = FuncRule(
        resource_kind=None,
        matches_fn=tracking_match,
        verdict_fn=simple_verdict,
    )
    fc = make_field_change()
    assert rule.matches(fc) == True
    assert received[0] is fc


def test_funcrule_matches_fn_on_field_path():
    rule = FuncRule(
        resource_kind=None,
        matches_fn=lambda fc: fc.field_path == "spec.replicas",
        verdict_fn=simple_verdict,
    )
    assert rule.matches(make_field_change(field_path="spec.replicas")) == True
    assert rule.matches(make_field_change(field_path="spec.image")) == False


def test_funcrule_match_fn_on_value_change():
    rule = FuncRule(
        resource_kind="Deployment",
        matches_fn=lambda fc: fc.new_value == "Recreate",
        verdict_fn=simple_verdict,
    )
    assert rule.matches(make_field_change(new_value="Recreate")) == True
    assert rule.matches(make_field_change(new_value="RollingUpdate")) == False


def test_funcrule_verdict_returns_impact_verdict():
    rule = FuncRule(
        resource_kind="Deployment", matches_fn=alway_match, verdict_fn=simple_verdict
    )
    fc = make_field_change()
    result = rule.verdict(fc)
    assert isinstance(result, ImpactVerdict)


def test_funcrule_verdict_fn_receives_field_change():
    received = []

    def capturing_verdict(change):
        received.append(change)
        return make_verdict(change)

    fc = make_field_change()
    rule = FuncRule(
        resource_kind="Deployment", matches_fn=alway_match, verdict_fn=capturing_verdict
    )
    result = rule.verdict(fc)
    assert received[0] is fc


def test_funcrule_verdict_reflects_severity():
    rule = FuncRule(
        resource_kind="Deployment",
        matches_fn=alway_match,
        verdict_fn=lambda c: make_verdict(c, severity=Severity.DANGER),
    )
    fc = make_field_change()
    result = rule.verdict(fc)
    assert result.severity == Severity.DANGER


def test_funcrule_verdict_reflects_kind():
    rule = FuncRule(
        resource_kind="Deployment",
        matches_fn=alway_match,
        verdict_fn=lambda c: make_verdict(c, kind=ImpactKind.DATA_LOSS_RISK),
    )
    fc = make_field_change()
    result = rule.verdict(fc)
    assert result.kind == ImpactKind.DATA_LOSS_RISK


def test_funcrule_verdict_attaches_field_change():
    fc = make_field_change(field_path="spec.replicas", old_value=2, new_value=5)
    rule = FuncRule(
        resource_kind="Deployment",
        matches_fn=alway_match,
        verdict_fn=lambda c: make_verdict(c),
    )
    result = rule.verdict(fc)
    assert result.field_change is fc


def test_funcrule_verdict_uses_dynamic_description():
    rule = FuncRule(
        resource_kind="Deployment",
        matches_fn=alway_match,
        verdict_fn=lambda c: make_verdict(
            c, description=f"Replicas changed from {c.old_value} -> {c.new_value}"
        ),
    )
    fc = make_field_change(field_path="spec.replicas", old_value=2, new_value=5)
    result = rule.verdict(fc)
    assert result.description == "Replicas changed from 2 -> 5"


def test_funcrule_is_instance_of_rule():
    rule = FuncRule(
        resource_kind="Deployment", matches_fn=alway_match, verdict_fn=simple_verdict
    )
    assert isinstance(rule, Rule)


def test_funcrule_satisfies_rule_interface():
    rule = FuncRule(
        resource_kind="Deployment", matches_fn=alway_match, verdict_fn=simple_verdict
    )
    fc = make_field_change()
    assert isinstance(rule.matches(fc), bool)
    assert isinstance(rule.verdict(fc), ImpactVerdict)
