import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.model import Severity
from core.model import ImpactKind
from core.model import FieldChange
from core.model import ImpactVerdict

from core.rules.base import Rule


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
