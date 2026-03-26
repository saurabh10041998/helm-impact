import re
import yaml
from typing import Any, Iterator


def load_manifest(yaml_text: str) -> list[dict]:
    """
    A single helm template output may contain multiple YAML documents separated by '---'.
    Parse them all
    """
    docs = yaml.safe_load_all(yaml_text)
    return [doc for doc in docs if doc is not None]


def resource_identity(manifest: dict) -> str:
    """
    Unique key for k8s resource: (kind, namespace, name)
    Used to pair old vs new versions of the same resource.
    """
    return (
        manifest.get("kind", ""),
        manifest.get("metadata", {}).get("namespace", "default"),
        manifest.get("metadata", {}).get("name", ""),
    )


def flatten(obj: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    """
    Recursively walk a nested dict/list and yield (dotted_path, leaf_value)
    Examples:
        {"spec":{"replicas": 3}} -> ("spec.replicas", 3)
        {"spec":{"template":{"spec":{"containers":[{"image":"nginx"}]}}}} -> ("spec.template.spec.containers.[0].image", "nginx")
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            yield from flatten(v, path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            path = f"{prefix}.[{i}]"
            yield from flatten(item, path)
    else:
        yield prefix, obj


def normalize_index(path: str) -> str:
    """
    Convert "spec.template.spec.containers.[0].image" to "spec.template.spec.containers.[*].image"
    This allows rules to match any index in a list
    """
    return re.sub(r"\.\[\d+\]", ".[*]", path)