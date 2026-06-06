import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.model import Severity
from core.model import ImpactKind
from core.model import FieldChange
from core.model import ImpactVerdict
from core.rules.rolebinding import _rolebinding_rules


def make_field_change(**kwargs) -> FieldChange:
    defaults = dict(
        resource_kind="RoleBinding",
        resource_name="my-binding",
        field_path="subjects.[*].name",
        old_value="alice",
        new_value="bob",
    )
    return FieldChange(**{**defaults, **kwargs})


def evaluate_one(fc: FieldChange) -> ImpactVerdict | None:
    rules = _rolebinding_rules()
    for rule in rules:
        if rule.matches(fc):
            return rule.verdict(fc)
    return None


def test_rolebinding_rules_returns_non_empty_list():
    rules = _rolebinding_rules()
    assert isinstance(rules, list)
    assert len(rules) > 0


def test_all_rules_have_rolebinding_resource_kind():
    assert all(r.resource_kind == "RoleBinding" for r in _rolebinding_rules())


def test_all_rules_have_name():
    assert all(r.name != "" for r in _rolebinding_rules())


def test_rules_do_not_match_wrong_resource_kind():
    fc = make_field_change(resource_kind="Role")
    for rule in _rolebinding_rules():
        assert rule.matches(fc) is False


def test_roleref_change_is_danger():
    fc = make_field_change(
        field_path="roleRef.name", old_value="reader", new_value="admin"
    )
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.DANGER
    assert verdict.kind == ImpactKind.MANNUAL_INTERVENTION


def test_subjects_change_is_warning():
    fc = make_field_change(field_path="subjects.[*].name")
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.WARNING
    assert verdict.kind == ImpactKind.MANNUAL_INTERVENTION


def test_unmatched_change_falls_back_to_info():
    fc = make_field_change(field_path="metadata.labels.team")
    verdict = evaluate_one(fc)
    assert verdict is not None
    assert verdict.severity == Severity.INFO
    assert verdict.kind == ImpactKind.UNCLEAR
