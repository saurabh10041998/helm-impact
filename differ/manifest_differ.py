from core.model import FieldChange
from differ.utils import resource_identity
from differ.utils import flatten
from differ.utils import normalize_index


class ManifestDiffer:
    def diff(
        self, old_manifest: list[dict], new_manifest: list[dict]
    ) -> list[FieldChange]:
        changes: list[FieldChange] = []

        old_by_id = {resource_identity(m): m for m in old_manifest}
        new_by_id = {resource_identity(m): m for m in new_manifest}

        all_ids = set(old_by_id) | set(new_by_id)

        for resource_id in all_ids:
            kind, namespace, name = resource_id
            old_res = old_by_id.get(resource_id)
            new_res = new_by_id.get(resource_id)

            if old_res is None:
                changes.append(
                    FieldChange(
                        resource_kind=kind,
                        resource_name=name,
                        field_path="<resource>",
                        old_value=None,
                        new_value="<created>",
                    )
                )
                continue

            if new_res is None:
                changes.append(
                    FieldChange(
                        resource_kind=kind,
                        resource_name=name,
                        field_path="<resource>",
                        old_value="<existed>",
                        new_value=None,
                    )
                )
                continue

            changes.extend(self._diff_resource(kind, name, old_res, new_res))

        return changes

    def _diff_resource(
        self, kind: str, name: str, old_res: dict, new_res: dict
    ) -> list[FieldChange]:
        changes: list[FieldChange] = []

        old_flat = dict(flatten(old_res))
        new_flat = dict(flatten(new_res))

        all_paths = set(old_flat) | set(new_flat)

        for raw_path in all_paths:
            old_value = old_flat.get(raw_path)
            new_value = new_flat.get(raw_path)

            if old_value == new_value:
                continue

            normalize_path = normalize_index(raw_path)

            if _is_noise(normalize_path):
                continue

            changes.append(
                FieldChange(
                    resource_kind=kind,
                    resource_name=name,
                    field_path=normalize_path,
                    old_value=old_value,
                    new_value=new_value,
                )
            )

        return changes


def _is_noise(path: str) -> bool:
    noise_prefixes = [
        "metadata.annotations.kubectl.kubernetes.io/last-applied",
        "metadata.annotations.deployment.kubernetes.io/revision",
        "metadata.resourceVersion",
        "metadata.uid",
        "status.",
    ]
    return any(path.startswith(prefix) for prefix in noise_prefixes)
