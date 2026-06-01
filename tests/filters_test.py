import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.model import FieldChange
from core.model import ImpactKind
from core.model import ImpactVerdict
from core.model import Severity
from tools.filters import filter_by_resource


def make_verdict(kind: str, name: str) -> ImpactVerdict:
    change = FieldChange(
        resource_kind=kind,
        resource_name=name,
        field_path="spec.replicas",
        old_value=2,
        new_value=5,
    )
    return ImpactVerdict(
        severity=Severity.INFO,
        kind=ImpactKind.SCALE_EVENT,
        description="",
        remediation="",
        field_change=change,
    )


def kinds(verdicts: list[ImpactVerdict]) -> list[str]:
    return [v.field_change.resource_kind for v in verdicts]


VERDICTS = [
    make_verdict("Deployment", "api"),
    make_verdict("StatefulSet", "db"),
    make_verdict("PersistentVolumeClaim", "db-data"),
]


def test_no_filter_returns_all():
    assert filter_by_resource(VERDICTS) == VERDICTS


def test_include_by_kind():
    result = filter_by_resource(VERDICTS, include=["Deployment"])
    assert kinds(result) == ["Deployment"]


def test_include_by_name():
    result = filter_by_resource(VERDICTS, include=["db"])
    assert kinds(result) == ["StatefulSet"]


def test_include_multiple():
    result = filter_by_resource(VERDICTS, include=["Deployment", "StatefulSet"])
    assert kinds(result) == ["Deployment", "StatefulSet"]


def test_exclude_by_kind():
    result = filter_by_resource(VERDICTS, exclude=["PersistentVolumeClaim"])
    assert kinds(result) == ["Deployment", "StatefulSet"]


def test_exclude_by_name():
    result = filter_by_resource(VERDICTS, exclude=["api"])
    assert kinds(result) == ["StatefulSet", "PersistentVolumeClaim"]


def test_empty_lists_return_all():
    assert filter_by_resource(VERDICTS, include=[], exclude=[]) == VERDICTS
