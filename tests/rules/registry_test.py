import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.model import ImpactKind
from core.model import FieldChange
from core.rules.registry import build_engine


def test_build_engine_resolves_new_kinds_to_non_unclear():
    engine = build_engine()
    impactful_changes = [
        FieldChange(
            resource_kind="ServiceAccount",
            resource_name="sa",
            field_path="automountServiceAccountToken",
            old_value=True,
            new_value=False,
        ),
        FieldChange(
            resource_kind="PodDisruptionBudget",
            resource_name="pdb",
            field_path="spec.minAvailable",
            old_value=1,
            new_value=2,
        ),
        FieldChange(
            resource_kind="Secret",
            resource_name="sec",
            field_path="data.password",
            old_value="a",
            new_value="b",
        ),
        FieldChange(
            resource_kind="Role",
            resource_name="role",
            field_path="rules.[*].verbs.[*]",
            old_value="get",
            new_value="delete",
        ),
        FieldChange(
            resource_kind="RoleBinding",
            resource_name="rb",
            field_path="roleRef.name",
            old_value="reader",
            new_value="admin",
        ),
    ]

    for change in impactful_changes:
        verdict = engine.evaluate(change)
        assert verdict.kind != ImpactKind.UNCLEAR, change.resource_kind
