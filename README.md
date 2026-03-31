[![Tests](https://github.com/saurabh10041998/helm-impact/actions/workflows/test.yml/badge.svg)](https://github.com/saurabh10041998/helm-impact/actions/workflows/test.yml)

# helm-impact
helm upgrade impact analyzer plugin

# demo
![demo](assets/screencast.svg)

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
    └── renderer.py              # various report renders

```
