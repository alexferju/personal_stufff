"""
Architectural Constraints — mechanically enforces dependency layer rules.

Harness Principle: Constraints improve output. When an agent can generate
anything, it wastes tokens exploring dead ends. Constrain the solution
space to make agents more productive.
"""
from typing import NamedTuple

LAYERS = ["types", "config", "domain", "service", "api", "ui"]

LAYER_DESCRIPTIONS = {
    "types":   "Pure data types, enums, dataclasses. No external project dependencies.",
    "config":  "Configuration and settings. May import from: types.",
    "domain":  "Business logic and rules. May import from: types, config.",
    "service": "External services, DB access. May import from: types, config, domain.",
    "api":     "HTTP handlers, routes. May import from: types, config, domain, service.",
    "ui":      "User interfaces. May import from all layers.",
    "infra":   "Infrastructure/scripts. May import from all layers.",
}


class LayerViolation(NamedTuple):
    task_id: str
    task_layer: str
    dep_id: str
    dep_layer: str
    description: str


def get_allowed_imports(layer: str) -> list[str]:
    """Returns layers this layer may import from."""
    if layer not in LAYERS:
        return list(LAYERS)
    idx = LAYERS.index(layer)
    return LAYERS[:idx]


def get_constraint_prompt(layer: str) -> str:
    """Returns a constraint string for injection into agent system prompts."""
    allowed = get_allowed_imports(layer)
    desc = LAYER_DESCRIPTIONS.get(layer, "General purpose layer.")
    if allowed:
        return (
            f"Layer '{layer}': {desc} "
            f"ONLY import from: {', '.join(allowed)}. "
            f"NEVER import from: {', '.join(l for l in LAYERS if l not in allowed and l != layer)}."
        )
    return f"Layer '{layer}': {desc} No dependencies on other layers allowed."


def validate_layer_order(tasks: list[dict]) -> list[LayerViolation]:
    """
    Validates that task dependency graph respects layer ordering.
    A lower-layer task cannot depend on a higher-layer task.
    """
    task_map = {t["id"]: t for t in tasks}
    violations = []

    for task in tasks:
        task_layer = task.get("layer", "domain")
        for dep_id in task.get("depends_on", []):
            dep = task_map.get(dep_id)
            if not dep:
                continue
            dep_layer = dep.get("layer", "domain")
            if dep_layer in LAYERS and task_layer in LAYERS:
                dep_idx = LAYERS.index(dep_layer)
                task_idx = LAYERS.index(task_layer)
                if dep_idx > task_idx:
                    violations.append(LayerViolation(
                        task_id=task["id"],
                        task_layer=task_layer,
                        dep_id=dep_id,
                        dep_layer=dep_layer,
                        description=(
                            f"{task['id']} ({task_layer}) depends on {dep_id} ({dep_layer}) "
                            f"— lower layer cannot depend on higher layer"
                        ),
                    ))
    return violations
