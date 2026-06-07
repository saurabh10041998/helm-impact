from core.rules.engine import RuleEngine
from core.rules.deployment import _deployment_rules
from core.rules.pvc import _pvc_rules
from core.rules.statefulset import _statefulset_rules
from core.rules.serviceaccount import _serviceaccount_rules
from core.rules.poddisruptionbudget import _poddisruptionbudget_rules
from core.rules.secret import _secret_rules
from core.rules.role import _role_rules
from core.rules.rolebinding import _rolebinding_rules


def build_engine() -> RuleEngine:
    engine = RuleEngine()
    for rule in _deployment_rules():
        engine.register(rule)
    for rule in _statefulset_rules():
        engine.register(rule)
    for rule in _pvc_rules():
        engine.register(rule)
    for rule in _serviceaccount_rules():
        engine.register(rule)
    for rule in _poddisruptionbudget_rules():
        engine.register(rule)
    for rule in _secret_rules():
        engine.register(rule)
    for rule in _role_rules():
        engine.register(rule)
    for rule in _rolebinding_rules():
        engine.register(rule)
    return engine


def supported_resource_kinds() -> list[str]:
    """Resource kinds that have at least one rule implemented, sorted."""
    return build_engine().resource_kinds()
