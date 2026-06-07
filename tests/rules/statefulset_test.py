import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.model import Severity
from core.model import ImpactKind
from core.model import FieldChange
from core.model import ImpactVerdict
from core.rules.statefulset import _statefulset_rules


def make_field_change(**kwargs) -> FieldChange:
    defaults = dict(
        resource_kind="StatefulSet",
        resource_name="my-db",
        field_path="spec.replicas",
        old_value=2,
        new_value=5,
    )
    return FieldChange(**{**defaults, **kwargs})


def evaluate(changes: list[FieldChange]) -> list[ImpactVerdict]:
    rules = _statefulset_rules()
    results = []
    for change in changes:
        for rule in rules:
            if rule.matches(change):
                results.append(rule.verdict(change))
                break

    return results


def evaluate_one(fc: FieldChange) -> ImpactVerdict | None:
    rules = _statefulset_rules()
    for rule in rules:
        if rule.matches(fc):
            return rule.verdict(fc)

    return None


def test_statefulset_rules_returns_list():
    assert isinstance(_statefulset_rules(), list)


def test_statefulset_rules_not_empty():
    assert len(_statefulset_rules()) > 0


def test_all_rules_have_statefulset_resource_kind():
    assert all(rule.resource_kind == "StatefulSet" for rule in _statefulset_rules())


def test_all_rules_have_name():
    for rule in _statefulset_rules():
        assert rule.name != ""


def test_rules_do_not_match_wrong_resource_kind():
    fc = make_field_change(
        resource_kind="Deployment",
        field_path="spec.template.spec.containers.[*].image",
    )
    for rule in _statefulset_rules():
        assert rule.matches(fc) is False


# --- image-change ---


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
    assert evaluate_one(fc).severity == Severity.WARNING


def test_image_change_kind_is_rolling_restart():
    fc = make_field_change(
        field_path="spec.template.spec.containers.[*].image",
        old_value="v1.0.0",
        new_value="v1.1.0",
    )
    assert evaluate_one(fc).kind == ImpactKind.ROLLING_RESTART


def test_image_change_description_has_no_trailing_typo():
    fc = make_field_change(
        field_path="spec.template.spec.containers.[*].image",
        old_value="v1.0.0",
        new_value="v1.1.0",
    )
    assert evaluate_one(fc).description.endswith("v1.1.0")


def test_image_change_init_container_matches():
    fc = make_field_change(
        field_path="spec.template.spec.initContainers.[*].image",
        old_value="v1.0.0",
        new_value="v1.1.0",
    )
    assert evaluate_one(fc).kind == ImpactKind.ROLLING_RESTART


# --- volume-claim-template-change ---


def test_volume_claim_template_change_severity_is_danger():
    fc = make_field_change(
        field_path="spec.volumeClaimTemplates.[*].spec.resources.requests.storage",
        old_value="10Gi",
        new_value="20Gi",
    )
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.DANGER
    assert verdict.kind == ImpactKind.DATA_LOSS_RISK


def test_volume_claim_template_remediation_mentions_immutable():
    fc = make_field_change(
        field_path="spec.volumeClaimTemplates.[*].spec.resources.requests.storage",
        old_value="10Gi",
        new_value="20Gi",
    )
    assert "immutable" in evaluate_one(fc).remediation.lower()


# --- immutable scalar fields ---


def test_service_name_change_is_danger_manual():
    fc = make_field_change(
        field_path="spec.serviceName", old_value="db", new_value="db2"
    )
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.DANGER
    assert verdict.kind == ImpactKind.MANNUAL_INTERVENTION


def test_selector_change_is_danger():
    fc = make_field_change(
        field_path="spec.selector.matchLabels.app",
        old_value="db",
        new_value="db2",
    )
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.DANGER
    assert verdict.kind == ImpactKind.MANNUAL_INTERVENTION


def test_pod_management_policy_change_is_danger():
    fc = make_field_change(
        field_path="spec.podManagementPolicy",
        old_value="OrderedReady",
        new_value="Parallel",
    )
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.DANGER
    assert verdict.kind == ImpactKind.MANNUAL_INTERVENTION


# --- update-strategy-change ---


def test_update_strategy_ondelete_is_danger_manual():
    fc = make_field_change(
        field_path="spec.updateStrategy.type",
        old_value="RollingUpdate",
        new_value="OnDelete",
    )
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.DANGER
    assert verdict.kind == ImpactKind.MANNUAL_INTERVENTION


def test_update_strategy_rollingupdate_is_warning_restart():
    fc = make_field_change(
        field_path="spec.updateStrategy.type",
        old_value="OnDelete",
        new_value="RollingUpdate",
    )
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.WARNING
    assert verdict.kind == ImpactKind.ROLLING_RESTART


# --- replicas-change ---


def test_replicas_scale_up_is_info_scale_event():
    fc = make_field_change(field_path="spec.replicas", old_value=2, new_value=5)
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.INFO
    assert verdict.kind == ImpactKind.SCALE_EVENT


def test_replicas_scale_down_remediation_warns():
    fc = make_field_change(field_path="spec.replicas", old_value=5, new_value=2)
    assert "scale down" in evaluate_one(fc).remediation.lower()


def test_replicas_scale_up_remediation_is_benign():
    fc = make_field_change(field_path="spec.replicas", old_value=2, new_value=5)
    assert "scale up" in evaluate_one(fc).remediation.lower()


# --- resource-limit-change ---


def test_resource_limit_change_is_warning_restart():
    fc = make_field_change(
        field_path="spec.template.spec.containers.[*].resources.limits.memory",
        old_value="256Mi",
        new_value="512Mi",
    )
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.WARNING
    assert verdict.kind == ImpactKind.ROLLING_RESTART


# --- fallback ---


def test_unknown_spec_field_hits_fallback():
    fc = make_field_change(field_path="spec.someNewField", old_value=1, new_value=2)
    verdict = evaluate_one(fc)
    assert verdict is not None
    assert verdict.severity == Severity.INFO
    assert verdict.kind == ImpactKind.UNCLEAR


def test_metadata_change_hits_fallback():
    fc = make_field_change(
        field_path="metadata.labels.team", old_value="a", new_value="b"
    )
    assert evaluate_one(fc).kind == ImpactKind.UNCLEAR


def test_fallback_rule_is_last():
    rules = _statefulset_rules()
    assert rules[-1].name == "fallback"
