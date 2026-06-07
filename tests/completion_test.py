import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.rules.registry import supported_resource_kinds
from tools.completion import _bash_script
from tools.completion import _zsh_script

EXPECTED_KINDS = [
    "Deployment",
    "PersistentVolumeClaim",
    "PodDisruptionBudget",
    "Role",
    "RoleBinding",
    "Secret",
    "ServiceAccount",
    "StatefulSet",
]


def test_supported_resource_kinds_matches_registered_rules():
    assert supported_resource_kinds() == EXPECTED_KINDS


def test_supported_resource_kinds_is_sorted_and_unique():
    kinds = supported_resource_kinds()
    assert kinds == sorted(kinds)
    assert len(kinds) == len(set(kinds))


def test_bash_script_completes_resource_flags_with_kinds():
    script = _bash_script()
    assert "--resource|--hide-resource)" in script
    assert 'resource_kinds="' in script
    for kind in EXPECTED_KINDS:
        assert kind in script


def test_zsh_script_completes_resource_flags_with_kinds():
    script = _zsh_script()
    assert "--resource" in script
    assert "--hide-resource" in script
    for kind in EXPECTED_KINDS:
        assert kind in script
