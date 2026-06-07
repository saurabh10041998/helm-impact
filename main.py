import argparse
import sys

from tools.analyzer import analyze
from tools.chart import ChartRenderError
from tools.chart import render_chart
from tools.completion import generate_completion
from tools.filters import filter_by_resource
from tools.renderer import TableRenderer


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
    parser.add_argument(
        "--from-values",
        dest="from_values",
        action="append",
        metavar="VALUES.yaml",
        help=(
            "Override values file for the from chart "
            "(passed to helm template as -f; repeatable, later files win)"
        ),
    )
    parser.add_argument(
        "--to-values",
        dest="to_values",
        action="append",
        metavar="VALUES.yaml",
        help=(
            "Override values file for the to chart "
            "(passed to helm template as -f; repeatable, later files win)"
        ),
    )
    resource_filter = parser.add_mutually_exclusive_group()
    resource_filter.add_argument(
        "--resource",
        action="append",
        metavar="KIND_OR_NAME",
        help=(
            "Only show impact for this resource (by kind or name; "
            "repeat the flag to pass several, e.g. "
            "--resource Deployment --resource StatefulSet)"
        ),
    )
    resource_filter.add_argument(
        "--hide-resource",
        dest="hide_resource",
        action="append",
        metavar="KIND_OR_NAME",
        help=(
            "Hide impact for this resource (by kind or name; "
            "repeat the flag to pass several, e.g. "
            "--hide-resource Secret --hide-resource Role)"
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
        old_manifest_text = render_chart(args.from_chart, values_files=args.from_values)
        new_manifest_text = render_chart(args.to_chart, values_files=args.to_values)
    except ChartRenderError as exc:
        sys.exit(f"error: {exc}")

    verdicts = analyze(old_manifest_text, new_manifest_text)
    verdicts = filter_by_resource(
        verdicts,
        include=args.resource or [],
        exclude=args.hide_resource or [],
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
