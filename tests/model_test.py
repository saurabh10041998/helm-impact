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
