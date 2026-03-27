import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from model import Severity


class TestSeverityEnum:
    def test_all_values_exist(self):
        assert Severity.INFO.value == "info"
        assert Severity.WARNING.value == "warning"
        assert Severity.DANGER.value == "danger"
        assert Severity.BLOCKER.value == "blocker"

    def test_count(self):
        assert len(Severity) == 4

    def test_from_value(self):
        assert Severity("info") == Severity.INFO
        assert Severity("warning") == Severity.WARNING
        assert Severity("danger") == Severity.DANGER
        assert Severity("blocker") == Severity.BLOCKER

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            Severity("critical")
