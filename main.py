import argparse
import sys

from tools.analyzer import analyze
from tools.chart import ChartRenderError
from tools.chart import render_chart
from tools.filters import filter_by_resource
from tools.renderer import TableRenderer


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _flatten(values: list[list[str]] | None) -> list[str]:
    if not values:
        return []
    return [item for group in values for item in group]


def main():
    parser = argparse.ArgumentParser(
        description="Analyze the impact of upgrading a Helm chart"
    )
    parser.add_argument(
        "--from",
        dest="from_chart",
        required=True,
        metavar="CHART.tgz",
        help="Path to the current (from) packaged Helm chart .tgz",
    )
    parser.add_argument(
        "--to",
        dest="to_chart",
        required=True,
        metavar="CHART.tgz",
        help="Path to the upgraded (to) packaged Helm chart .tgz",
    )
    resource_filter = parser.add_mutually_exclusive_group()
    resource_filter.add_argument(
        "--resource",
        type=_csv,
        action="append",
        metavar="KIND_OR_NAME",
        help=(
            "Only show impact for these resources "
            "(comma-separated, by kind or name; repeatable)"
        ),
    )
    resource_filter.add_argument(
        "--hide-resource",
        dest="hide_resource",
        type=_csv,
        action="append",
        metavar="KIND_OR_NAME",
        help=(
            "Hide impact for these resources "
            "(comma-separated, by kind or name; repeatable)"
        ),
    )
    args = parser.parse_args()

    try:
        old_manifest_text = render_chart(args.from_chart)
        new_manifest_text = render_chart(args.to_chart)
    except ChartRenderError as exc:
        sys.exit(f"error: {exc}")

    verdicts = analyze(old_manifest_text, new_manifest_text)
    verdicts = filter_by_resource(
        verdicts,
        include=_flatten(args.resource),
        exclude=_flatten(args.hide_resource),
    )
    TableRenderer().render_report(verdicts)


if __name__ == "__main__":
    main()
