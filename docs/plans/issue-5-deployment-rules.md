# Plan: Issue #5 — Extend the Deployment ruleset

**Issue:** [#5 — Extend the ruleset of deployment](https://github.com/saurabh10041998/helm-impact/issues/5)
**Branch (proposed):** `feature/issue-5-deployment-rules`
**Status:** Planning — **no code changes yet.**

---

## 1. Problem statement

`core/rules/deployment.py` currently registers **only four** rules:

1. `image-change` (WARNING / ROLLING_RESTART)
2. `replicas-change` (INFO / SCALE_EVENT)
3. `strategy-type-change` (DANGER|WARNING / DOWNTIME|ROLLING_RESTART)
4. `resource-limit-change` (WARNING / ROLLING_RESTART)

Two structural gaps stand out when compared against the newer, richer
`statefulset.py` (9 rules, written for issue #4):

- **No catch-all `fallback` rule.** Any Deployment field change that doesn't
  match one of the four rules falls through to the `RuleEngine` default verdict.
  StatefulSet/RBAC modules instead end with an explicit `INFO` / `UNCLEAR`
  fallback so every change surfaces as at least a low-severity row.
- **Missing coverage for common, impactful Deployment changes** — most notably
  `spec.selector` (which is **immutable** on a Deployment, like StatefulSet's),
  plus env/probe/command/volume/port changes that all trigger a rolling restart
  but currently produce a generic "no rule matched" verdict.

Goal: extend the Deployment ruleset to classify the common upgrade changes with
meaningful severity / impact / remediation, on par with the StatefulSet ruleset,
and add the missing fallback.

---

## 2. How the codebase expects this to be done

Per `CLAUDE.md` and the existing modules (`deployment.py`, `statefulset.py`):

- Rules live in `core/rules/deployment.py` as
  `_deployment_rules() -> list[FuncRule]`.
- **First-match wins** (`RuleEngine.evaluate`) — order rules **most-specific →
  least-specific** within the factory; the `fallback` rule must be **last**.
- **Paths are normalized** — list indices arrive as `.[*]`
  (`differ/utils.normalize_index`). Match against e.g.
  `spec.template.spec.containers.[*].image`, never raw indexed paths.
- **Glob helpers already exist** in `deployment.py`: reuse `_path_matches` and
  `_any_path_matches`. Per the issue-3/issue-4 decision, the shared-helper
  extraction stays **deferred** — keep the helpers duplicated locally.
- **No new model values needed** — `Severity` (INFO/WARNING/DANGER/BLOCKER) and
  `ImpactKind` (ROLLING_RESTART, DOWNTIME, DATA_LOSS_RISK, MANNUAL_INTERVENTION,
  SCALE_EVENT, NO_IMPACT, UNCLEAR) already cover every case below.
  *(Note the existing enum spelling `MANNUAL_INTERVENTION` — match it exactly.)*
- **Registry** — `_deployment_rules()` is **already wired** in
  `registry.py::build_engine()`; no registry edit required.
- **Import convention** — one `from ... import x` per line (project rule).

---

## 3. Proposed rules

Existing rules are kept; new rules are marked **(new)**. Ordered most-specific →
least-specific. Severities are a starting proposal, open to tuning in review.

| # | Rule name | Match (`field_path`) | Severity | ImpactKind | Rationale |
|---|-----------|----------------------|----------|------------|-----------|
| 1 | `selector-change` **(new)** | `spec.selector.*` | DANGER | MANNUAL_INTERVENTION | `spec.selector` is **immutable** on a Deployment — the apply is rejected; needs delete + recreate. Must rank above template rules. |
| 2 | `image-change` *(existing)* | `spec.template.spec.containers.[*].image`, `…initContainers.[*].image` | WARNING | ROLLING_RESTART | Image swap → rolling restart. |
| 3 | `resource-limit-change` *(existing)* | `…containers/initContainers.[*].resources.{limits,requests}.*` | WARNING | ROLLING_RESTART | Resource change → pod template change → rolling restart. |
| 4 | `env-change` **(new)** | `…containers/initContainers.[*].env.*`, `…envFrom.*` | WARNING | ROLLING_RESTART | Env/envFrom change alters the pod template → rolling restart. |
| 5 | `probe-change` **(new)** | `…containers.[*].{livenessProbe,readinessProbe,startupProbe}.*` | WARNING | ROLLING_RESTART | Probe changes can affect rollout health gating; triggers restart. |
| 6 | `command-args-change` **(new)** | `…containers/initContainers.[*].{command,args}.*` | WARNING | ROLLING_RESTART | Entrypoint/args change → rolling restart; behaviour may change. |
| 7 | `volume-change` **(new)** | `spec.template.spec.volumes.*`, `…containers.[*].volumeMounts.*` | WARNING | ROLLING_RESTART | Volume/mount change → rolling restart; verify data paths. |
| 8 | `port-change` **(new)** | `…containers.[*].ports.*` | WARNING | ROLLING_RESTART | Container port change → rolling restart; check Service wiring. |
| 9 | `service-account-change` **(new)** | `spec.template.spec.serviceAccountName` | WARNING | ROLLING_RESTART | Identity/permission change → rolling restart; verify RBAC. |
| 10 | `replicas-change` *(existing)* | `spec.replicas` | INFO* | SCALE_EVENT | Scale up/down; value-dependent remediation. *See note on scale-to-zero. |
| 11 | `strategy-type-change` *(existing)* | `spec.strategy.type` | DANGER\|WARNING | DOWNTIME\|ROLLING_RESTART | `Recreate` → downtime (DANGER); `RollingUpdate` → WARNING/restart. |
| 12 | `strategy-rolling-params-change` **(new)** | `spec.strategy.rollingUpdate.{maxUnavailable,maxSurge}` | WARNING | ROLLING_RESTART | Rollout pacing change; `maxUnavailable>0` can reduce capacity mid-roll. |
| 13 | `fallback` **(new)** | any other | INFO | UNCLEAR | Catch-all so unmatched churn still surfaces as a low-severity row (mirrors StatefulSet/RBAC modules). Must be **last**. |

Notes / decisions to confirm in review:

- **Ordering:** `selector-change` (immutable) ranks first so a forbidden-update
  is reported as such rather than as a benign restart. `strategy-type-change`
  stays ahead of `strategy-rolling-params-change` (it's an exact-path match, so
  order is not strictly required, but keeps related rules grouped).
- **Rules 2–9** all collapse to WARNING / ROLLING_RESTART. They are kept as
  *separate named rules* (rather than one mega-rule) to give each a precise
  description/remediation and targeted tests — consistent with how
  `statefulset.py` and the issue-3 RBAC modules are structured. If review
  prefers fewer rules, candidates 4–9 could be merged into a single
  `pod-template-change` rule; flagged as an open question (§6).
- **Scale-to-zero (rule 10):** consider whether `spec.replicas: N -> 0` should
  escalate to DANGER / DOWNTIME (full outage) rather than INFO / SCALE_EVENT.
  Open question (§6); the existing rule keeps INFO today.
- **Value-dependent rules** (10, 11) reuse the existing branch-on-`c.new_value`
  pattern already in the file.
- **Fallback (rule 13)** uses `Severity.INFO` + `ImpactKind.UNCLEAR` (not
  `NO_IMPACT`, which `analyze()` filters out) so the row survives and is visible
  — same convention as StatefulSet's `fallback`.

---

## 4. File-by-file change list

1. **Edit:** `core/rules/deployment.py`
   - Add new rules 1, 4–9, 12, and the `fallback` (rule 13), in the order above.
   - Reuse the existing `_path_matches` / `_any_path_matches` helpers (no new
     helper needed).
   - Keep existing rules' wording; only re-order to slot in the new ones.
2. **Edit:** `tests/rules/deployment_test.py`
   - Add per-rule tests for each new rule (mirror the StatefulSet test module:
     local `make_field_change(resource_kind="Deployment", ...)`, `evaluate` /
     `evaluate_one` first-match helpers, `sys.path.insert(...)` at top;
     one-import-per-line).
   - Add a `fallback`-is-last assertion and a negative/`status.*` case.
3. **No edit** to `core/rules/registry.py` — already registers
   `_deployment_rules()`.
4. **Optional edit:** `Makefile` `format` target *only if* it enumerates files
   explicitly — confirm whether `deployment_test.py` is already covered (it
   exists today, so likely yes).

---

## 5. Testing & verification

Per-rule unit tests asserting `severity`, `kind`, and that the description
contains the changed path/values, plus:

- `selector-change` returns DANGER / MANNUAL_INTERVENTION and mentions
  immutable / recreate.
- `image-change`, `env-change`, `probe-change`, `command-args-change`,
  `volume-change`, `port-change`, `service-account-change`,
  `resource-limit-change` each return WARNING / ROLLING_RESTART for both
  `containers` and (where applicable) `initContainers` paths.
- `replicas-change` scale-up vs scale-down remediation wording (and scale-to-zero
  if that decision lands as DANGER).
- `strategy-type-change` both branches (`Recreate` vs `RollingUpdate`).
- `strategy-rolling-params-change` matches `maxUnavailable` and `maxSurge`.
- `fallback`: an unknown `spec.*` field returns INFO / UNCLEAR; and assert the
  `fallback` rule is **last** in `_deployment_rules()`.
- Negative cases: `status.*` and a wrong-`resource_kind` change match no
  specific rule (and that `_is_noise` already drops `status.*` upstream).

Commands (from `CLAUDE.md`):

- `pytest -v` (full suite — also confirms `registry_test.py` still passes).
- `flake8` (max-line-length 88).
- `make format` before opening the PR.
- Manual smoke: craft a before/after Deployment manifest pair exercising an
  image bump, an env change, a `spec.selector` edit, and a strategy flip, then
  run `helm-impact old.yaml new.yaml` and confirm the table shows the new
  verdicts instead of "No rule matched".

---

## 6. Open questions (for review before implementation)

1. **Rule granularity** — keep rules 4–9 as separate named rules, or collapse
   into one `pod-template-change` (WARNING / ROLLING_RESTART) rule? Separate
   rules give better messages/tests; merged is fewer lines. *Proposed: keep
   separate, consistent with StatefulSet.*
2. **Scale-to-zero severity** — should `spec.replicas -> 0` escalate to
   DANGER / DOWNTIME? *Proposed: yes, as a value-dependent branch in
   `replicas-change`; confirm.*
3. **`deployment.py` shared-helper extraction** — still **deferred** (helpers
   stay duplicated across rule modules), per the issue-3/issue-4 decision.
   Confirm we are not extracting in this PR.
4. **Probe path scope** — match `*Probe.*` broadly, or only the
   commonly-tuned sub-fields? *Proposed: broad `*Probe.*`, simplest and safe.*
