# Plan: Issue #3 — Add verdict support for additional resource types

**Issue:** [#3 — Add support for verdict on some of the following resource types](https://github.com/saurabh10041998/helm-impact/issues/3)
**Branch:** `feature/issue-3-resource-verdicts`
**Status:** Planning — no code changes yet.

### Decisions (resolved with author)
- **Scope:** all five kinds in **one PR**.
- **Severity:** keep DANGER picks as **DANGER** (no BLOCKER escalation).
- **Benign metadata churn:** **surface as INFO** — do *not* silence via `NO_IMPACT`.
- **Refactor (§5):** **defer** — duplicate `_path_matches` per module for now.

---

## 1. Problem statement

When `helm-impact` diffs charts that contain RBAC / supporting resources, those
kinds have **no registered rules**, so every change falls through to the
`RuleEngine` default verdict (`WARNING` / `UNCLEAR`, "No rule matched ...").

From the issue, the affected kinds are:

| Kind | Typical churn we should classify |
|------|----------------------------------|
| `ServiceAccount` | annotations (IRSA / workload-identity), `automountServiceAccountToken`, `imagePullSecrets`, secret refs |
| `PodDisruptionBudget` | `spec.minAvailable`, `spec.maxUnavailable`, `spec.selector` |
| `Secret` | `data.*` / `stringData.*`, `type`, whole-resource add/remove |
| `Role` | `rules.[*]` (verbs/resources/apiGroups) |
| `RoleBinding` | `roleRef`, `subjects.[*]` |

Goal: emit **meaningful** severity / impact / remediation for the common changes
on each kind, and a sensible non-`UNCLEAR` fallback for the rest.

---

## 2. How the codebase expects this to be done

The extension path is already documented in `CLAUDE.md` and exercised by
`deployment.py`, `statefulset.py`, `pvc.py`:

1. Create `core/rules/<kind>.py` exposing a `_<kind>_rules() -> list[FuncRule]` factory.
2. Register the factory in `core/rules/registry.py` `build_engine()`.
3. Add a `tests/rules/<kind>_test.py` module.

Key mechanics confirmed by reading the source:

- **First-match wins** — `RuleEngine.evaluate` (`core/rules/engine.py`) returns the
  verdict of the first rule whose `matches()` is true, so **order rules
  most-specific → least-specific** within each factory.
- **Paths are normalized** — list indices arrive as `.[*]` (see
  `differ/utils.normalize_index`). Match against e.g. `rules.[*].verbs.[*]`,
  never raw indexed paths.
- **Glob matching helper** — `_path_matches` / `_any_path_matches` in
  `deployment.py` convert `*` → regex `.*`. This helper is currently duplicated
  in `deployment.py` and `statefulset.py`. See §5 (optional refactor).
- **Whole-resource add/remove** — `ManifestDiffer.diff` emits a single
  `FieldChange` with `field_path="<resource>"`, `new_value="<created>"` (added)
  or `old_value="<existed>"` (removed). New rule sets should handle this path
  where add/remove is impactful (notably `Secret`, `RoleBinding`).
- **`NO_IMPACT` is filtered** — `tools/analyzer.analyze` drops verdicts whose
  `kind == ImpactKind.NO_IMPACT`. Use `NO_IMPACT` to intentionally silence
  benign churn (e.g. a `ServiceAccount` label change) so it disappears from the
  table instead of showing as noise.
- **No new model values needed** — `Severity` (INFO/WARNING/DANGER/BLOCKER) and
  `ImpactKind` (ROLLING_RESTART, DOWNTIME, DATA_LOSS_RISK, MANNUAL_INTERVENTION,
  SCALE_EVENT, NO_IMPACT, UNCLEAR) in `core/model.py` already cover these cases.

---

## 3. Proposed rules per kind

Severities below are a starting proposal — open to tuning during review.

> **Fallback convention (per author decision):** benign / unmatched changes are
> surfaced as `INFO` rather than silenced. Since `analyze()` filters out
> `NO_IMPACT`, the catch-all rule uses `Severity.INFO` + `ImpactKind.UNCLEAR`
> (which survives the filter) so the row still appears, just at low severity.

### 3.1 `core/rules/serviceaccount.py`
| Rule | Match (`field_path`) | Severity | ImpactKind | Notes |
|------|----------------------|----------|------------|-------|
| `automount-token-change` | `automountServiceAccountToken` | WARNING | MANNUAL_INTERVENTION | Toggling token mounting can break/expose pods |
| `image-pull-secrets-change` | `imagePullSecrets.*` | WARNING | ROLLING_RESTART | Image pulls may fail until pods restart |
| `iam-annotation-change` | `metadata.annotations.*` (e.g. `eks.amazonaws.com/role-arn`, `iam.gke.io/*`) | WARNING | MANNUAL_INTERVENTION | Cloud identity binding changed |
| (fallback) | any other | INFO | UNCLEAR | Surface benign churn as low-severity row |

### 3.2 `core/rules/poddisruptionbudget.py`
| Rule | Match | Severity | ImpactKind | Notes |
|------|-------|----------|------------|-------|
| `min-available-change` | `spec.minAvailable` | WARNING | MANNUAL_INTERVENTION | Affects voluntary disruption / node drains |
| `max-unavailable-change` | `spec.maxUnavailable` | WARNING | MANNUAL_INTERVENTION | Same axis as above |
| `selector-change` | `spec.selector.*` | DANGER | MANNUAL_INTERVENTION | PDB may stop protecting intended pods |
| (fallback) | any other | INFO | UNCLEAR | Surface as low-severity row |

### 3.3 `core/rules/secret.py`
| Rule | Match | Severity | ImpactKind | Notes |
|------|-------|----------|------------|-------|
| `secret-removed` | `field_path == "<resource>"` and `new_value is None` | DANGER | DATA_LOSS_RISK | Consumers may fail to mount |
| `secret-added` | `field_path == "<resource>"` and `new_value == "<created>"` | INFO | MANNUAL_INTERVENTION | New secret — surface for awareness |
| `secret-type-change` | `type` | DANGER | MANNUAL_INTERVENTION | Type is immutable on a live Secret |
| `secret-data-change` | `data.*` / `stringData.*` | WARNING | ROLLING_RESTART | Pods need restart to pick up env/volume; **do not print values** |
| (fallback) | any other | INFO | UNCLEAR | Surface as low-severity row |

> ⚠️ **Security:** never put `old_value`/`new_value` of `Secret` `data` into the
> description or remediation. Report only the key/path that changed.

### 3.4 `core/rules/role.py`
| Rule | Match | Severity | ImpactKind | Notes |
|------|-------|----------|------------|-------|
| `rules-change` | `rules.[*].*` (verbs/resources/apiGroups/resourceNames) | WARNING | MANNUAL_INTERVENTION | Permission surface changed — review for least-privilege |
| (fallback) | any other | INFO | UNCLEAR | Surface as low-severity row |

### 3.5 `core/rules/rolebinding.py`
| Rule | Match | Severity | ImpactKind | Notes |
|------|-------|----------|------------|-------|
| `roleref-change` | `roleRef.*` | DANGER | MANNUAL_INTERVENTION | `roleRef` is immutable — requires delete+recreate |
| `subjects-change` | `subjects.[*].*` | WARNING | MANNUAL_INTERVENTION | Who-has-access changed |
| (fallback) | any other | INFO | UNCLEAR | Surface as low-severity row |

---

## 4. File-by-file change list

1. **New:** `core/rules/serviceaccount.py` — `_serviceaccount_rules()`
2. **New:** `core/rules/poddisruptionbudget.py` — `_poddisruptionbudget_rules()`
3. **New:** `core/rules/secret.py` — `_secret_rules()`
4. **New:** `core/rules/role.py` — `_role_rules()`
5. **New:** `core/rules/rolebinding.py` — `_rolebinding_rules()`
6. **Edit:** `core/rules/registry.py` — import each factory and `register()` its
   rules in `build_engine()` (follow existing `for rule in _x_rules(): engine.register(rule)` pattern; honor the project's one-import-per-line convention).
7. **New tests:** `tests/rules/serviceaccount_test.py`, `poddisruptionbudget_test.py`,
   `secret_test.py`, `role_test.py`, `rolebinding_test.py` — mirror
   `deployment_test.py` (local `make_field_change`, `evaluate_one`, `sys.path.insert`).
8. **Edit (optional):** `Makefile` `format` target if it enumerates files explicitly
   — add the new modules so `make format` covers them.

---

## 5. Optional refactor (call out, decide during review)

`_path_matches` / `_any_path_matches` are duplicated in `deployment.py` and
`statefulset.py`, and all five new modules will need them. Options:

- **A (minimal):** duplicate the helper again in each new module — consistent with
  current code, zero blast radius.
- **B (cleaner):** extract `_path_matches` / `_any_path_matches` into
  `core/rules/base.py` (or a new `core/rules/matchers.py`) and import everywhere,
  removing the duplication.

Recommendation was **B**, but **author chose to defer**: for this PR we go with
**option A** — duplicate the `_path_matches` / `_any_path_matches` helper in each
new module to match current code and minimize blast radius. The shared-helper
extraction can be revisited in a follow-up.

---

## 6. Testing & verification

- Per-kind unit tests: each impactful path → asserts on `severity`, `kind`,
  description contains changed path, and benign paths return the `NO_IMPACT`
  fallback (or `None` in the local `evaluate_one` helper).
- One `registry` sanity check that `build_engine()` now resolves a known change
  for each new kind to something **other than** `UNCLEAR`.
- Run `pytest -v`, `flake8`, `make format` before opening the PR.
- Manual smoke: craft a small before/after manifest pair containing these kinds
  and run `helm-impact old.yaml new.yaml` to confirm the table no longer shows
  "No rule matched" for them.

---

## 7. Resolved decisions

1. **Severity calibration** — keep DANGER picks (PDB selector, Secret
   removal/type, `roleRef`) as **DANGER**; no BLOCKER escalation. ✅
2. **ServiceAccount/metadata churn** — **surface as INFO** (not silenced). ✅
3. **Scope** — implement **all five kinds in one PR**. ✅
4. **Refactor** — **defer** §5 option B; duplicate the matcher helper per module
   for now. ✅
