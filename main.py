import argparse
from tools.analyzer import analyze
from tools.renderer import TableRenderer


def main():
    parser = argparse.ArgumentParser(description="Analyze Helm manifest changes")
    parser.add_argument("old_manifest", help="Path to the old manifest YAML file")
    parser.add_argument("new_manifest", help="Path to the new manifest YAML file")
    args = parser.parse_args()

    old_manifest_text = open(args.old_manifest).read()
    new_manifest_text = open(args.new_manifest).read()

    verdicts = analyze(old_manifest_text, new_manifest_text)
    output = TableRenderer()
    output.render_report(verdicts)
