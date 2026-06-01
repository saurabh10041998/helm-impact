import argparse
import sys

from tools.analyzer import analyze
from tools.chart import ChartRenderError
from tools.chart import render_chart
from tools.renderer import TableRenderer


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
    args = parser.parse_args()

    try:
        old_manifest_text = render_chart(args.from_chart)
        new_manifest_text = render_chart(args.to_chart)
    except ChartRenderError as exc:
        sys.exit(f"error: {exc}")

    verdicts = analyze(old_manifest_text, new_manifest_text)
    TableRenderer().render_report(verdicts)


if __name__ == "__main__":
    main()
