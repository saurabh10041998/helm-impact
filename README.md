[![Tests](https://github.com/saurabh10041998/helm-impact/actions/workflows/test.yml/badge.svg)](https://github.com/saurabh10041998/helm-impact/actions/workflows/test.yml)

# helm-impact
helm upgrade impact analyzer plugin

It renders two packaged Helm charts (the current and the upgraded version),
diffs the resulting manifests, and reports the impact of each change
(rolling restart, downtime, data-loss risk, ...) as a severity-ranked table.

# prerequisites
- Python 3.9+
- [Helm](https://helm.sh/docs/intro/install/) available on your `PATH` (used to
  render charts via `helm template`)

# installation
```bash
make all   # or: pip3 install -e .
```
This installs the `helm-impact` console script.

# usage
```bash
helm-impact --from <current-chart.tgz> --to <upgraded-chart.tgz> [filter]
```

| Option            | Description                                                                    |
| ----------------- | ----------------------------------------------------------------------------- |
| `--from`          | Path to the current (from) packaged Helm chart .tgz                            |
| `--to`            | Path to the upgraded (to) packaged Helm chart .tgz                             |
| `--from-values`   | Override values file for the `--from` chart (repeatable)                       |
| `--to-values`     | Override values file for the `--to` chart (repeatable)                         |
| `--resource`      | Only show impact for these resources (comma-separated, by kind or name)        |
| `--hide-resource` | Hide impact for these resources (comma-separated, by kind or name)            |

`--resource` and `--hide-resource` are mutually exclusive. Both accept a
comma-separated list and can be repeated; values match either the resource
**kind** (e.g. `Deployment`) or its **name** (e.g. `my-app`).

## example
```bash
# package the chart at two revisions, then compare them
helm package ./myapp --version 1.0.0 -d ./charts
helm package ./myapp --version 1.1.0 -d ./charts

helm-impact --from ./charts/myapp-1.0.0.tgz --to ./charts/myapp-1.1.0.tgz

# only show impact for Deployments and StatefulSets
helm-impact --from ./charts/myapp-1.0.0.tgz --to ./charts/myapp-1.1.0.tgz \
  --resource Deployment,StatefulSet

# show everything except PersistentVolumeClaim changes
helm-impact --from ./charts/myapp-1.0.0.tgz --to ./charts/myapp-1.1.0.tgz \
  --hide-resource PersistentVolumeClaim
```

## value overrides
Some charts require values to be supplied before they can render (e.g. a
`Required value "xyz" is missing from the config` error). Pass an override
values file with `--from-values` / `--to-values` — these are forwarded to
`helm template` as `-f` flags, exactly like a normal `helm` invocation. Both
flags are repeatable, and when given multiple files later files win:
```bash
# render each side with its own overrides
helm-impact --from ./charts/myapp-1.0.0.tgz --to ./charts/myapp-1.1.0.tgz \
  --from-values ./values/old.yaml \
  --to-values ./values/new.yaml

# layer multiple overrides on a single side (base first, then env-specific)
helm-impact --from ./charts/myapp-1.0.0.tgz --to ./charts/myapp-1.1.0.tgz \
  --to-values ./values/base.yaml --to-values ./values/prod.yaml
```

# shell completion
Generate a completion script for your shell. The platform is detected
automatically — **bash** on Linux, **zsh** on macOS — and the command prints
instructions on how to source it.
```bash
helm-impact completion
```

# project structure
```bash
helm-impact
├── core
│   ├── __init__.py
│   ├── model.py                 # core data structure to denote change and its verdict
│   └── rules
│       ├── __init__.py
│       ├── base.py              # basic rule definition
│       ├── engine.py            # houses rule engine
│       ├── registry.py          # rules registry
│       ├── deployment.py        # verdict rules for deployment change
│       ├── statefulset.py       # verdict rules for statefulset change
│       ├── pvc.py               # verdict rules for pvc change
│       ├── secret.py            # verdict rules for secret change
│       ├── serviceaccount.py    # verdict rules for serviceaccount change
│       ├── role.py              # verdict rules for role change
│       ├── rolebinding.py       # verdict rules for rolebinding change
│       └── poddisruptionbudget.py  # verdict rules for poddisruptionbudget change
├── differ
│   ├── __init__.py
│   ├── manifest_differ.py       # manifest diff calculator
│   └── utils.py                 # helper utils for diff calculation
├── tools
│   ├── __init__.py
│   ├── analyzer.py              # main analyzer
│   ├── chart.py                 # renders helm chart .tgz into a flat manifest
│   ├── completion.py            # generates bash/zsh shell completion scripts
│   ├── filters.py               # filters verdicts by resource kind/name
│   └── renderer.py              # various report renders
├── tests                        # pytest suite (non-source; mirrors layout above)
├── LICENSE
├── main.py                      # entry point
├── Makefile
├── README.md
├── spec.md                      # project specification
├── setup.cfg
└── setup.py
```
