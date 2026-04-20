"""
Architecture fitness tests.

Two categories:

1. STRICT  — new clean layers (domain, ports, application, adapters).
             Any violation is a hard CI failure.

2. TRACKING — legacy app/routes layer, which still imports app/services
              directly while the PR2-PR6 migration is in progress.
              The test caps violations at the current known count so that:
              - existing violations are tolerated,
              - adding NEW violations fails CI immediately.
"""

import ast
import pathlib
import pytest

BACKEND = pathlib.Path(__file__).parent.parent


# ── Helpers ──────────────────────────────────────────────────────────────────

def _imports_in_file(path: pathlib.Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module)
    return modules


def _py_files(layer: str) -> list[pathlib.Path]:
    return sorted((BACKEND / layer).rglob("*.py"))


def _violations(layer: str, forbidden: list[str]) -> list[tuple[str, str]]:
    """Return (relative_file, import) pairs that breach the forbidden list."""
    out = []
    for path in _py_files(layer):
        for imp in _imports_in_file(path):
            if any(imp == f or imp.startswith(f + ".") for f in forbidden):
                out.append((str(path.relative_to(BACKEND)), imp))
    return out


# ── Strict layer rules ────────────────────────────────────────────────────────
#
# Allowed import direction:
#   domain  ← nothing (pure Python + stdlib only)
#   ports   ← domain
#   application ← domain, ports
#   adapters    ← domain, ports, application  (not app.services / app.routes)
#
# Each entry: (layer_dir, forbidden_top_level_prefixes)

STRICT_RULES: list[tuple[str, list[str]]] = [
    ("domain",      ["app", "ports", "application", "adapters"]),
    ("ports",       ["app", "application", "adapters"]),
    ("application", ["app", "adapters"]),
    ("adapters",    ["services", "routes"]),
]


@pytest.mark.parametrize("layer,forbidden", STRICT_RULES, ids=[r[0] for r in STRICT_RULES])
def test_layer_boundary(layer: str, forbidden: list[str]) -> None:
    bad = _violations(layer, forbidden)
    assert bad == [], (
        f"Layer '{layer}' has forbidden cross-layer imports:\n"
        + "\n".join(f"  {f}  →  {imp}" for f, imp in bad)
    )


# ── Tracking: legacy routes → services (migration cap) ───────────────────────
#
# This count reflects the state at the time of PR1 (before PR2-PR6 migration).
# Decrement it as each PR eliminates route→service coupling.
# Increasing it (adding new violations) causes an immediate CI failure.

_KNOWN_ROUTE_SERVICE_VIOLATIONS = 6


def test_legacy_route_service_coupling_does_not_grow() -> None:
    violations = _violations("routes", ["services"])
    count = len(violations)
    assert count <= _KNOWN_ROUTE_SERVICE_VIOLATIONS, (
        f"Route→service coupling grew: {count} violations (cap: {_KNOWN_ROUTE_SERVICE_VIOLATIONS}).\n"
        f"New violations:\n"
        + "\n".join(f"  {f}  →  {imp}" for f, imp in violations)
    )
    remaining = _KNOWN_ROUTE_SERVICE_VIOLATIONS - count
    if remaining > 0:
        pytest.fail(
            f"Cap is still {_KNOWN_ROUTE_SERVICE_VIOLATIONS} but only {count} violations remain. "
            f"Lower _KNOWN_ROUTE_SERVICE_VIOLATIONS to {count} to lock in the improvement.",
            pytrace=False,
        )
