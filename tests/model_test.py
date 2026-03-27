import pytest
from core.model import Severity


class TestSeverityEnum:
    def test_all_values_exist(self):
        assert Severity.INFO.value == "info"
        assert Severity.WARNING.value == "warning"
        assert Severity.DANGER.value == "danger"
        assert Severity.BLOCKER.value == "blocker"
