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
helm-impact --from <current-chart.tgz> --to <upgraded-chart.tgz>
```

| Option   | Description                                        |
| -------- | -------------------------------------------------- |
| `--from` | Path to the current (from) packaged Helm chart .tgz |
| `--to`   | Path to the upgraded (to) packaged Helm chart .tgz  |

## example
```bash
# package the chart at two revisions, then compare them
helm package ./myapp --version 1.0.0 -d ./charts
helm package ./myapp --version 1.1.0 -d ./charts

helm-impact --from ./charts/myapp-1.0.0.tgz --to ./charts/myapp-1.1.0.tgz
```

# project structure
```bash
helm-impact
├── core
│   ├── __init__.py
│   ├── model.py                 # core data structure to denote change and its verdict
│   └── rules
│       ├── __init__.py
│       ├── base.py              # basic rule definition
│       ├── engine.py            #  houses rule engine
│       ├── registry.py          #  rules registry
│       ├── pvc.py               #  verdict rules for pvc  change
│       ├── statefulset.py       #  verdict rules for statefulset change
│       └── deployment.py        #  verdict rules for deployment change
├── differ
│   ├── __init__.py
│   ├── manifest_differ.py       # manifest diff calculator
│   └── utils.py                 # helper utils for diff calculation
├── LICENSE
├── main.py                      # entry points
├── Makefile
├── README.md
├── setup.cfg
├── setup.py
└── tools
    ├── __init__.py
    ├── analyzer.py              # main analyzer
    ├── chart.py                 # renders helm chart .tgz into a flat manifest
    └── renderer.py              # various report renders

```
