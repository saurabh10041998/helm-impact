import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from differ.manifest_differ import ManifestDiffer
from differ.manifest_differ import _is_noise


def _deployment(chart_label: str, version_label: str, image: str) -> dict:
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "my-app",
            "namespace": "default",
            "labels": {
                "helm.sh/chart": chart_label,
                "app.kubernetes.io/version": version_label,
            },
        },
        "spec": {
            "template": {
                "metadata": {
                    "labels": {
                        "helm.sh/chart": chart_label,
                        "app.kubernetes.io/version": version_label,
                    },
                },
                "spec": {
                    "containers": [
                        {"name": "app", "image": image},
                    ]
                },
            }
        },
    }


def test_is_noise_skips_helm_chart_label():
    assert _is_noise("metadata.labels.helm.sh/chart") is True


def test_is_noise_skips_app_version_label():
    assert _is_noise("metadata.labels.app.kubernetes.io/version") is True


def test_is_noise_keeps_other_labels():
    assert _is_noise("metadata.labels.app.kubernetes.io/name") is False
    assert _is_noise("metadata.labels.team") is False


def test_is_noise_skips_template_helm_chart_label():
    assert _is_noise("spec.template.metadata.labels.helm.sh/chart") is True


def test_is_noise_skips_template_app_version_label():
    assert _is_noise("spec.template.metadata.labels.app.kubernetes.io/version") is True


def test_is_noise_keeps_other_template_labels():
    assert _is_noise("spec.template.metadata.labels.app.kubernetes.io/name") is False


def test_version_labels_are_filtered_from_diff():
    old = [_deployment("app-1.0.0", "1.0.0", "app:1.0.0")]
    new = [_deployment("app-1.1.0", "1.1.0", "app:1.0.0")]

    changes = ManifestDiffer().diff(old, new)

    noisy = [
        c
        for c in changes
        if c.field_path
        in (
            "metadata.labels.helm.sh/chart",
            "metadata.labels.app.kubernetes.io/version",
            "spec.template.metadata.labels.helm.sh/chart",
            "spec.template.metadata.labels.app.kubernetes.io/version",
        )
    ]
    assert noisy == []


def test_real_changes_still_reported_alongside_noisy_labels():
    old = [_deployment("app-1.0.0", "1.0.0", "app:1.0.0")]
    new = [_deployment("app-1.1.0", "1.1.0", "app:2.0.0")]

    changes = ManifestDiffer().diff(old, new)

    image_changes = [c for c in changes if c.field_path.endswith(".image")]
    assert len(image_changes) == 1
    assert image_changes[0].old_value == "app:1.0.0"
    assert image_changes[0].new_value == "app:2.0.0"
