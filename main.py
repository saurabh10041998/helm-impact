import argparse
import sys

from tools.analyzer import analyze
from tools.chart import ChartRenderError
from tools.chart import render_chart
from tools.completion import generate_completion
from tools.filters import filter_by_resource
from tools.renderer import TableRenderer


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _flatten(values: list[list[str]] | None) -> list[str]:
    if not values:
        return []
    return [item for group in values for item in group]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="helm-impact",
        description="Analyze the impact of upgrading a Helm chart",
    )
    parser.add_argument(
        "--from",
        dest="from_chart",
        metavar="CHART.tgz",
        help="Path to the current (from) packaged Helm chart .tgz",
    )
    parser.add_argument(
        "--to",
        dest="to_chart",
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

    commands = parser.add_subparsers(dest="command")
    commands.add_parser(
        "completion",
        help="Generate a shell completion script for your platform",
    )
    return parser


def _run_analysis(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if not args.from_chart or not args.to_chart:
        parser.error("--from and --to are required")

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


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "completion":
        generate_completion()
        return

    _run_analysis(parser, args)


if __name__ == "__main__":
    main()
