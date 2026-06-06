import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.model import Severity
from core.model import ImpactKind
from core.model import FieldChange
from core.model import ImpactVerdict
from core.rules.role import _role_rules


def make_field_change(**kwargs) -> FieldChange:
    defaults = dict(
        resource_kind="Role",
        resource_name="my-role",
        field_path="rules.[*].verbs.[*]",
        old_value="get",
        new_value="delete",
    )
    return FieldChange(**{**defaults, **kwargs})


def evaluate_one(fc: FieldChange) -> ImpactVerdict | None:
    rules = _role_rules()
    for rule in rules:
        if rule.matches(fc):
            return rule.verdict(fc)
    return None


def test_role_rules_returns_non_empty_list():
    rules = _role_rules()
    assert isinstance(rules, list)
    assert len(rules) > 0


def test_all_rules_have_role_resource_kind():
    assert all(r.resource_kind == "Role" for r in _role_rules())


def test_all_rules_have_name():
    assert all(r.name != "" for r in _role_rules())


def test_rules_do_not_match_wrong_resource_kind():
    fc = make_field_change(resource_kind="RoleBinding")
    for rule in _role_rules():
        assert rule.matches(fc) is False


def test_rules_verbs_change():
    fc = make_field_change(field_path="rules.[*].verbs.[*]")
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.WARNING
    assert verdict.kind == ImpactKind.MANNUAL_INTERVENTION


def test_rules_resources_change():
    fc = make_field_change(field_path="rules.[*].resources.[*]")
    verdict = evaluate_one(fc)
    assert verdict.kind == ImpactKind.MANNUAL_INTERVENTION


def test_unmatched_change_falls_back_to_info():
    fc = make_field_change(field_path="metadata.labels.team")
    verdict = evaluate_one(fc)
    assert verdict is not None
    assert verdict.severity == Severity.INFO
    assert verdict.kind == ImpactKind.UNCLEAR
