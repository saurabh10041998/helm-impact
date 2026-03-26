# helm-impact
helm upgrade impact analyzer plugin

# project structure
```bash
helm-impact
├── core
│   ├── __init__.py
│   ├── model.py               # core data structure to denote change and its verdict
│   └── rules
│       ├── __init__.py
│       ├── base.py            # basic rule definition
│       ├── engine.py          #  houses rule engine
│       ├── registry.py        #  rules registry
│       ├── pvc.py             #  verdict rules for pvc  change
│       ├── statefulset.py     #  verdict rules for deployment change 
│       └── deployment.py      #  verdict rules for deployment change
├── LICENSE
├── main.py
├── Makefile
├── README.md
├── setup.cfg
└── setup.py


```