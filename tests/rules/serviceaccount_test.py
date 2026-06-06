import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.model import Severity
from core.model import ImpactKind
from core.model import FieldChange
from core.model import ImpactVerdict
from core.rules.serviceaccount import _serviceaccount_rules


def make_field_change(**kwargs) -> FieldChange:
    defaults = dict(
        resource_kind="ServiceAccount",
        resource_name="my-sa",
        field_path="automountServiceAccountToken",
        old_value=True,
        new_value=False,
    )
    return FieldChange(**{**defaults, **kwargs})


def evaluate_one(fc: FieldChange) -> ImpactVerdict | None:
    rules = _serviceaccount_rules()
    for rule in rules:
        if rule.matches(fc):
            return rule.verdict(fc)
    return None


def test_serviceaccount_rules_returns_non_empty_list():
    rules = _serviceaccount_rules()
    assert isinstance(rules, list)
    assert len(rules) > 0


def test_all_rules_have_serviceaccount_resource_kind():
    assert all(r.resource_kind == "ServiceAccount" for r in _serviceaccount_rules())


def test_all_rules_have_name():
    assert all(r.name != "" for r in _serviceaccount_rules())


def test_rules_do_not_match_wrong_resource_kind():
    fc = make_field_change(resource_kind="Deployment")
    for rule in _serviceaccount_rules():
        assert rule.matches(fc) is False


def test_automount_token_change():
    fc = make_field_change(field_path="automountServiceAccountToken")
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.WARNING
    assert verdict.kind == ImpactKind.MANNUAL_INTERVENTION


def test_image_pull_secrets_change():
    fc = make_field_change(field_path="imagePullSecrets.[*].name")
    verdict = evaluate_one(fc)
    assert verdict.kind == ImpactKind.ROLLING_RESTART


def test_iam_annotation_change():
    fc = make_field_change(
        field_path="metadata.annotations.eks.amazonaws.com/role-arn",
        old_value="arn:aws:iam::111:role/old",
        new_value="arn:aws:iam::111:role/new",
    )
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.WARNING
    assert verdict.kind == ImpactKind.MANNUAL_INTERVENTION


def test_unmatched_change_falls_back_to_info():
    fc = make_field_change(field_path="metadata.labels.team")
    verdict = evaluate_one(fc)
    assert verdict is not None
    assert verdict.severity == Severity.INFO
    assert verdict.kind == ImpactKind.UNCLEAR
