import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.model import Severity
from core.model import ImpactKind
from core.model import FieldChange
from core.model import ImpactVerdict
from core.rules.poddisruptionbudget import _poddisruptionbudget_rules


def make_field_change(**kwargs) -> FieldChange:
    defaults = dict(
        resource_kind="PodDisruptionBudget",
        resource_name="my-pdb",
        field_path="spec.minAvailable",
        old_value=1,
        new_value=2,
    )
    return FieldChange(**{**defaults, **kwargs})


def evaluate_one(fc: FieldChange) -> ImpactVerdict | None:
    rules = _poddisruptionbudget_rules()
    for rule in rules:
        if rule.matches(fc):
            return rule.verdict(fc)
    return None


def test_pdb_rules_returns_non_empty_list():
    rules = _poddisruptionbudget_rules()
    assert isinstance(rules, list)
    assert len(rules) > 0


def test_all_rules_have_pdb_resource_kind():
    rules = _poddisruptionbudget_rules()
    assert all(r.resource_kind == "PodDisruptionBudget" for r in rules)


def test_all_rules_have_name():
    assert all(r.name != "" for r in _poddisruptionbudget_rules())


def test_rules_do_not_match_wrong_resource_kind():
    fc = make_field_change(resource_kind="Deployment")
    for rule in _poddisruptionbudget_rules():
        assert rule.matches(fc) is False


def test_min_available_change():
    fc = make_field_change(field_path="spec.minAvailable", old_value=1, new_value=3)
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.WARNING
    assert verdict.kind == ImpactKind.MANNUAL_INTERVENTION
    assert "1" in verdict.description
    assert "3" in verdict.description


def test_max_unavailable_change():
    fc = make_field_change(field_path="spec.maxUnavailable", old_value=1, new_value=2)
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.WARNING
    assert verdict.kind == ImpactKind.MANNUAL_INTERVENTION


def test_selector_change_is_danger():
    fc = make_field_change(field_path="spec.selector.matchLabels.app")
    verdict = evaluate_one(fc)
    assert verdict.severity == Severity.DANGER
    assert verdict.kind == ImpactKind.MANNUAL_INTERVENTION


def test_unmatched_change_falls_back_to_info():
    fc = make_field_change(field_path="metadata.labels.team")
    verdict = evaluate_one(fc)
    assert verdict is not None
    assert verdict.severity == Severity.INFO
    assert verdict.kind == ImpactKind.UNCLEAR
