import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.chart import ChartRenderError
from tools.chart import render_chart


class _CompletedProcess:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout


def test_render_chart_passes_values_files(tmp_path, monkeypatch):
    chart = tmp_path / "app.tgz"
    chart.write_text("")
    values = tmp_path / "override.yaml"
    values.write_text("key: value\n")

    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return _CompletedProcess("rendered: true\n")

    monkeypatch.setattr("tools.chart.shutil.which", lambda _: "/usr/bin/helm")
    monkeypatch.setattr("tools.chart.subprocess.run", fake_run)

    out = render_chart(str(chart), values_files=[str(values)])

    assert out == "rendered: true\n"
    assert captured["command"][:4] == ["helm", "template", "release", str(chart)]
    assert captured["command"][-2:] == ["-f", str(values)]


def test_render_chart_multiple_values_files_in_order(tmp_path, monkeypatch):
    chart = tmp_path / "app.tgz"
    chart.write_text("")
    first = tmp_path / "a.yaml"
    first.write_text("")
    second = tmp_path / "b.yaml"
    second.write_text("")

    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return _CompletedProcess("")

    monkeypatch.setattr("tools.chart.shutil.which", lambda _: "/usr/bin/helm")
    monkeypatch.setattr("tools.chart.subprocess.run", fake_run)

    render_chart(str(chart), values_files=[str(first), str(second)])

    assert captured["command"][-4:] == ["-f", str(first), "-f", str(second)]


def test_render_chart_missing_values_file_raises(tmp_path, monkeypatch):
    chart = tmp_path / "app.tgz"
    chart.write_text("")

    monkeypatch.setattr("tools.chart.shutil.which", lambda _: "/usr/bin/helm")

    with pytest.raises(ChartRenderError, match="values file not found"):
        render_chart(str(chart), values_files=[str(tmp_path / "missing.yaml")])


def test_render_chart_no_values_files(tmp_path, monkeypatch):
    chart = tmp_path / "app.tgz"
    chart.write_text("")

    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return _CompletedProcess("")

    monkeypatch.setattr("tools.chart.shutil.which", lambda _: "/usr/bin/helm")
    monkeypatch.setattr("tools.chart.subprocess.run", fake_run)

    render_chart(str(chart))

    assert "-f" not in captured["command"]
