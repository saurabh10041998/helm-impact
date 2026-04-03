import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.model import Severity
from core.model import ImpactKind
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


def test_image_change_matches():
    fc = make_field_change(
        field_path="spec.template.spec.containers.[*].image",
        old_value="v1.0.0",
        new_value="v1.1.0",
    )
    verdict = evaluate_one(fc)
    assert verdict is not None


def test_image_change_severity_is_warning():
    fc = make_field_change(
        field_path="spec.template.spec.containers.[*].image",
        old_value="v1.0.0",
        new_value="v1.1.0",
    )
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.WARNING


def test_image_change_kind_is_rolling_restart():
    fc = make_field_change(
        field_path="spec.template.spec.containers.[*].image",
        old_value="v1.0.0",
        new_value="v1.1.0",
    )
    verdict = evaluate_one(fc)
    assert verdict.kind == ImpactKind.ROLLING_RESTART


def test_image_change_description_contains_old_and_new():
    fc = make_field_change(
        field_path="spec.template.spec.containers.[*].image",
        old_value="v1.0.0",
        new_value="v1.1.0",
    )
    verdict = evaluate_one(fc)
    assert "v1.0.0" in verdict.description
    assert "v1.1.0" in verdict.description


def test_image_change_init_container_matches():
    fc = make_field_change(
        field_path="spec.template.spec.initContainers.[*].image",
        old_value="v1.0.0",
        new_value="v1.1.0",
    )
    verdict = evaluate_one(fc)
    assert verdict is not None


def test_image_change_digest_format_matches():
    fc = make_field_change(
        field_path="spec.template.spec.containers.[*].image",
        old_value="my-app@sha256:abc123",
        new_value="my-app@sha256:def345",
    )
    verdict = evaluate_one(fc)
    verdict is not None


def test_replica_change_matches():
    fc = make_field_change(field_path="spec.replicas", old_value=2, new_value=5)
    verdict = evaluate_one(fc)
    verdict is not None


def test_replica_scale_up_severity_is_info():
    fc = make_field_change(field_path="spec.replicas", old_value=2, new_value=10)
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.INFO


def test_replica_scale_up_kind_is_scale_event():
    fc = make_field_change(field_path="spec.replicas", old_value=2, new_value=10)
    verdict = evaluate_one(fc)
    assert verdict.kind == ImpactKind.SCALE_EVENT


def test_replica_scale_down_remediation_warns():
    fc = make_field_change(field_path="spec.replicas", old_value=10, new_value=2)
    remediation = evaluate_one(fc).remediation.lower()
    assert "scale down" in remediation or "fewer" in remediation


def test_replica_scale_up_remediation_is_benign():
    fc = make_field_change(field_path="spec.replicas", old_value=2, new_value=10)
    remediation = evaluate_one(fc).remediation.lower()
    assert "scale up" in remediation or "no action" in remediation


def test_replica_change_to_zero_matches():
    fc = make_field_change(field_path="spec.replicas", old_value=3, new_value=0)
    verdict = evaluate_one(fc)
    assert verdict is not None
    assert verdict.kind == ImpactKind.SCALE_EVENT


def test_replica_change_description_contains_value():
    fc = make_field_change(field_path="spec.replicas", old_value=2, new_value=10)
    verdict = evaluate_one(fc)
    assert "2" in verdict.description
    assert "10" in verdict.description


def test_replica_unrelated_spec_field_does_not_match_rule():
    fc = make_field_change(field_path="spec.replicasFoo", old_value=2, new_value=5)
    rules = _deployment_rules()
    replica_rule = next(r for r in rules if r.name == "replicas-change")
    assert replica_rule.matches(fc) is False


def test_strategy_recreate_matches():
    fc = make_field_change(
        field_path="spec.strategy.type", old_value="RollingUpdate", new_value="Recreate"
    )
    verdict = evaluate_one(fc)
    assert verdict is not None


def test_strategy_recreate_severity_is_danger():
    fc = make_field_change(
        field_path="spec.strategy.type", old_value="RollingUpdate", new_value="Recreate"
    )
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.DANGER


def test_strategy_recreate_kind_is_downtime():
    fc = make_field_change(
        field_path="spec.strategy.type", old_value="RollingUpdate", new_value="Recreate"
    )
    verdict = evaluate_one(fc)
    assert verdict.kind == ImpactKind.DOWNTIME


def test_strategy_recreate_remediation_mentions_downtime():
    fc = make_field_change(
        field_path="spec.strategy.type", old_value="RollingUpdate", new_value="Recreate"
    )
    verdict = evaluate_one(fc)
    assert "downtime" in verdict.remediation.lower()


def test_strategy_rollingupdate_severity_is_warning():
    fc = make_field_change(
        field_path="spec.strategy.type", old_value="Recreate", new_value="RollingUpdate"
    )
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.WARNING


def test_strategy_rollingupdate_kind_is_rolling_restart():
    fc = make_field_change(
        field_path="spec.strategy.type", old_value="Recreate", new_value="RollingUpdate"
    )
    verdict = evaluate_one(fc)
    assert verdict.kind == ImpactKind.ROLLING_RESTART


def test_strategy_unrelated_path_does_not_match():
    fc = make_field_change(
        field_path="spec.strategy.RollingUpdate.maxSurge", old_value=1, new_value=2
    )
    rules = _deployment_rules()
    strategy_rule = next(rule for rule in rules if rule.name == "strategy-type-change")
    assert strategy_rule.matches(fc) is False

def test_resource_limit_matches():
    fc = make_field_change(
        field_path="spec.template.spec.containers.[*].resources.limits.memory",
        old_value="256Mi",
        new_value="512Mi"
    )
    verdict = evaluate_one(fc)
    assert verdict is not None