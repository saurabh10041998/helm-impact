from rich.console import Console
from rich.table import Table

from core.model import ImpactVerdict
from core.model import Severity


class TableRenderer:
    def render_report(self, verdicts: list[ImpactVerdict]) -> None:
        console = Console()
        table = Table(show_header=True, header_style="bold", show_lines=True)
        table.add_column("Resource")
        table.add_column("Field", overflow="fold")
        table.add_column("Severity")
        table.add_column("Impact")
        table.add_column("Description", overflow="fold")
        table.add_column("Remediation", overflow="fold")

        severity_colors = {
            Severity.INFO: "green",
            Severity.WARNING: "yellow",
            Severity.DANGER: "red",
            Severity.BLOCKER: "bold red",
        }

        for v in sorted(verdicts, key=lambda x: x.severity.value, reverse=True):
            color = severity_colors.get(v.severity, "white")
            table.add_row(
                f"{v.field_change.resource_kind}/{v.field_change.resource_name}",
                v.field_change.field_path,
                f"[{color}]{v.severity.name}[/{color}]",
                v.kind.name,
                v.description,
                v.remediation,
            )
        console.print(table)
