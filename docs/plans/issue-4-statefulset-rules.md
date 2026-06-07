# Plan: Issue #4 — Extend the StatefulSet ruleset

**Issue:** [#4 — Extend the rule set of statefulset](https://github.com/saurabh10041998/helm-impact/issues/4)
**Branch (proposed):** `feature/issue-4-statefulset-rules`
**Status:** Planning — **no code changes yet.**

---

## 1. Problem statement

`core/rules/statefulset.py` currently registers **exactly one** rule
(`image-change`). Every other StatefulSet field change falls through to the
`RuleEngine` default verdict (`WARNING` / `UNCLEAR`, "No rule matched ..."),
even though StatefulSets have several upgrade behaviours that are *more*
hazardous than a Deployment's — most notably **immutable spec fields** that
require a delete-and-recreate, and **`volumeClaimTemplates`** changes that are
silently ignored on existing pods and risk data loss.

The goal: classify the common StatefulSet upgrade changes with meaningful
severity / impact / remediation, on par with the Deployment ruleset.

### Existing rule — defects to fix while here
The current `image-change` rule has two small bugs worth correcting in this PR:
- `severity=Severity.INFO` — should be `WARNING` to match the Deployment image
  rule (an image swap triggers a rolling restart, not an informational no-op).
- Description ends in a stray `"t"`: `f"...to {c.new_value}t"` (same typo also
  present in `deployment.py`; fix at least the StatefulSet copy here).

---

## 2. How the codebase expects this to be done

Per `CLAUDE.md` and the existing modules (`deployment.py`, `pvc.py`):

- Rules live in `core/rules/statefulset.py` as `_statefulset_rules() -> list[FuncRule]`.
- **First-match wins** (`RuleEngine.evaluate`) — order rules **most-specific →
  least-specific** within the factory.
- **Paths are normalized** — list indices arrive as `.[*]`
  (`differ/utils.normalize_index`). Match against e.g.
  `spec.template.spec.containers.[*].image`, never raw indexed paths.
- **Glob helper** — reuse the `_path_matches` already defined in
  `statefulset.py`; add a local `_any_path_matches` (mirroring `deployment.py`)
  since several new rules match multiple paths. Per the issue-3 decision, the
  shared-helper extraction is **deferred** — keep the helper duplicated locally.
- **No new model values needed** — `Severity` (INFO/WARNING/DANGER/BLOCKER) and
  `ImpactKind` (ROLLING_RESTART, DOWNTIME, DATA_LOSS_RISK, MANNUAL_INTERVENTION,
  SCALE_EVENT, NO_IMPACT, UNCLEAR) already cover every case below.
- **Registry** — `_statefulset_rules()` is **already wired** in
  `registry.py::build_engine()`; no registry edit required.
- **Import convention** — one `from ... import x` per line (project rule).

---

## 3. Proposed rules

Ordered most-specific → least-specific. Severities are a starting proposal,
open to tuning during review.

| # | Rule name | Match (`field_path`) | Severity | ImpactKind | Rationale |
|---|-----------|----------------------|----------|------------|-----------|
| 1 | `image-change` *(existing, fix severity/typo)* | `spec.template.spec.containers.[*].image`, `spec.template.spec.initContainers.[*].image` | WARNING | ROLLING_RESTART | Image swap → rolling restart (governed by `updateStrategy`). |
| 2 | `volume-claim-template-change` | `spec.volumeClaimTemplates.*` | DANGER | DATA_LOSS_RISK | `volumeClaimTemplates` is **immutable**; changes are ignored on existing PVCs and a recreate can drop data. Requires manual PVC handling. |
| 3 | `service-name-change` | `spec.serviceName` | DANGER | MANNUAL_INTERVENTION | Immutable — kubectl/helm apply is rejected; needs delete + recreate. |
| 4 | `selector-change` | `spec.selector.*` | DANGER | MANNUAL_INTERVENTION | Immutable — same forbidden-update failure as above. |
| 5 | `pod-management-policy-change` | `spec.podManagementPolicy` | DANGER | MANNUAL_INTERVENTION | Immutable post-creation; delete + recreate required. |
| 6 | `update-strategy-change` | `spec.updateStrategy.type` | WARNING/DANGER | ROLLING_RESTART / MANNUAL_INTERVENTION | `OnDelete` → pods won't auto-update (manual delete needed, DANGER); `RollingUpdate` → WARNING / rolling restart. Mirror Deployment's `strategy-type-change` value-dependent branch. |
| 7 | `replicas-change` | `spec.replicas` | INFO | SCALE_EVENT | Scale up/down; value-dependent remediation like Deployment. Ordered StatefulSet pods mean scale-down terminates highest-ordinal first. |
| 8 | `resource-limit-change` | `spec.template.spec.containers.[*].resources.{limits,requests}.*` (+ initContainers) | WARNING | ROLLING_RESTART | Resource change → pod template change → rolling restart. |
| 9 | `fallback` | any other | INFO | UNCLEAR | Catch-all so benign/unmatched churn still surfaces as a low-severity row (mirrors the issue-3 RBAC modules). Must be **last**. |

Notes:
- Rules 2–5 (immutable fields) should rank **above** the template rules so a
  forbidden-update is reported as such rather than as a benign restart.
- For rule 6 reuse the value-dependent pattern from
  `deployment.py::strategy-type-change` (branch on `c.new_value`).
- Rule 9 uses `Severity.INFO` + `ImpactKind.UNCLEAR` (not `NO_IMPACT`, which
  `analyze()` filters out) so the row survives and is visible — same convention
  the issue-3 plan used for its fallbacks.

---

## 4. File-by-file change list

1. **Edit:** `core/rules/statefulset.py`
   - Add `_any_path_matches` helper (mirror `deployment.py`).
   - Fix existing `image-change` rule (severity `INFO` → `WARNING`, drop trailing
     `t` typo) and add the initContainers path.
   - Add rules 2–8 above.
2. **New:** `tests/rules/statefulset_test.py` — mirror `deployment_test.py`
   (local `make_field_change` with `resource_kind="StatefulSet"`, `evaluate` /
   `evaluate_one` helpers, `sys.path.insert(...)` at top; one-import-per-line).
3. **No edit** to `core/rules/registry.py` — already registers
   `_statefulset_rules()`.
4. **Optional edit:** `Makefile` `format` target *only if* it enumerates files
   explicitly — confirm whether the new test file needs adding so `make format`
   covers it.

---

## 5. Testing & verification

Per-rule unit tests asserting `severity`, `kind`, and that the description
contains the changed path/values, plus:
- `update-strategy-change` both branches (`OnDelete` vs `RollingUpdate`).
- `replicas-change` scale-up vs scale-down remediation wording.
- Immutable-field rules (serviceName/selector/podManagementPolicy/VCT) return
  DANGER and mention recreate/manual intervention.
- Negative cases: `status.*`, `metadata.labels.*`, and an unknown `spec.*` field
  return `None` from `evaluate_one` (no rule matches → engine default).
- Wrong-`resource_kind` change matches no rule.

Commands (from `CLAUDE.md`):
- `pytest -v` (full suite — also confirms `registry_test.py` still passes).
- `flake8` (max-line-length 88).
- `make format` before opening the PR.
- Manual smoke: craft a before/after StatefulSet manifest pair exercising an
  image bump, a `volumeClaimTemplates` size change, and an `updateStrategy`
  flip, then run `helm-impact old.yaml new.yaml` and confirm the table shows
  the new verdicts instead of "No rule matched".

---

## 6. Resolved decisions

1. **Immutable-field severity** — keep **DANGER** for serviceName / selector /
   podManagementPolicy / volumeClaimTemplates (no BLOCKER escalation), for
   consistency with the issue-3 decision. `volumeClaimTemplates` stays
   `DATA_LOSS_RISK`. ✅
2. **Catch-all fallback** — **add** an `INFO` / `UNCLEAR` fallback rule (rule 9
   above), matching the issue-3 RBAC modules so every StatefulSet change
   surfaces as at least a low-severity row. ✅
3. **`deployment.py` typo** — **leave it.** Keep this PR's diff scoped strictly
   to StatefulSet; the `{c.new_value}t` typo in `deployment.py` is handled
   separately. (The StatefulSet copy of the same typo is still fixed as part of
   the `image-change` cleanup in §4.) ✅
