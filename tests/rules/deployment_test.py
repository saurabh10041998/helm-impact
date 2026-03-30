import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.model import FieldChange
from core.model import ImpactVerdict
from core.rules.deployment import _deployment_rules


def make_field_change(**kwargs) -> FieldChange:
    defaults = dict(
        resource_kind="Deployment",
        resource_name="my-app",
        field_path="spec.replicas",
        old_value=2,
        new_value=5,
    )
    return FieldChange(**{**defaults, **kwargs})


def evaluate(changes: list[FieldChange]) -> list[ImpactVerdict]:
    rules = _deployment_rules()
    results = []
    for change in changes:
        for rule in rules:
            if rule.matches(change):
                results.append(rule.verdict(change))
                break

    return results


def evaluate_one(fc: FieldChange) -> ImpactVerdict | None:
    rules = _deployment_rules()
    for rule in rules:
        if rule.matches(fc):
            return rule.verdict(fc)

    return None


def test_deployment_rules_returns_list():
    assert isinstance(_deployment_rules(), list)


def test_deployment_rules_not_empty():
    assert len(_deployment_rules()) > 0


def test_all_rules_have_deployment_resource_kind():
    assert all(rule.resource_kind == "Deployment" for rule in _deployment_rules())


def test_all_rules_have_name():
    rules = _deployment_rules()
    for rule in rules:
        assert rule.name != ""


def test_rules_do_not_match_wrong_resource_kind():
    rules = _deployment_rules()
    fc = make_field_change(
        resource_kind="PersistentVolumeClaim",
        field_path="spec.template.spec.containers[*].image",
    )

    for rule in rules:
        assert rule.matches(fc) is False
