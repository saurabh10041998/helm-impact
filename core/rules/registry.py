from core.rules.engine import RuleEngine
from core.rules.deployment import _deployment_rules
from core.rules.pvc import _pvc_rules
from core.rules.statefulset import _statefulset_rules


def build_engine() -> RuleEngine:
    engine = RuleEngine()
    for rule in _deployment_rules():
        engine.register(rule)
    for rule in _statefulset_rules():
        engine.register(rule)
    for rule in _pvc_rules():
        engine.register(rule)
    return engine
