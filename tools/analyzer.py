from differ.manifest_differ import ManifestDiffer
from core.model import ImpactKind
from core.rules.registry import build_engine
from differ.utils import load_manifests


def analyze(old_yaml: str, new_yaml: str):
    old_manifest = load_manifests(old_yaml)
    new_manifest = load_manifests(new_yaml)

    differ = ManifestDiffer()
    changes = differ.diff(old_manifest, new_manifest)

    engine = build_engine()
    verdicts = engine.evaluate_all(changes)

    return [v for v in verdicts if v.kind != ImpactKind.NO_IMPACT]
