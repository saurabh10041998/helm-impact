import shutil
import subprocess
from pathlib import Path


class ChartRenderError(Exception):
    """Raised when a Helm chart cannot be rendered into a manifest."""


def render_chart(chart_path: str, release_name: str = "release") -> str:
    """
    Render a packaged Helm chart (.tgz) into a single flat manifest YAML.

    Shells out to `helm template`, whose output is a multi-document YAML
    stream that the analyzer already knows how to parse. Raises
    ChartRenderError (never a partial result) if anything goes wrong.
    """
    if shutil.which("helm") is None:
        raise ChartRenderError("helm executable not found on PATH")

    chart = Path(chart_path)
    if not chart.is_file():
        raise ChartRenderError(f"chart file not found: {chart}")

    try:
        result = subprocess.run(
            ["helm", "template", release_name, str(chart)],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or f"exit code {exc.returncode}"
        raise ChartRenderError(f"failed to render {chart}: {detail}") from exc

    return result.stdout
