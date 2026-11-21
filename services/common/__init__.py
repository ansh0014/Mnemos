"""Shared bootstrap utilities for Mnemos Python services.

Adds ``Mnemo/pipeline`` to ``sys.path`` so services reuse ``neuralloop_books`` directly,
and registers collision-free ``mnemos_services.<service_name>`` package aliases over the
hyphenated directories in ``Mnemos/services/`` (e.g. ``agent-challenge`` ->
``mnemos_services.agent_challenge``).
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

SERVICES_ROOT = Path(__file__).resolve().parent.parent
MNEMOS_ROOT = SERVICES_ROOT.parent
PIPELINE_ROOT = MNEMOS_ROOT / "Mnemo" / "pipeline"

SERVICE_ALIASES: dict[str, str] = {
    "common": "common",
    "ingestion_engine": "ingestion-engine",
    "memory_engine": "memory-engine",
    "agent_prime": "agent-prime",
    "agent_copilot": "agent-copilot",
    "agent_socratic": "agent-socratic",
    "agent_challenge": "agent-challenge",
}


def _register_namespace(pkg_name: str, pkg_dir: Path) -> None:
    """Register a directory as an importable package namespace if not already loaded."""
    if pkg_name in sys.modules:
        return
    init_file = pkg_dir / "__init__.py"
    if init_file.exists():
        spec = importlib.util.spec_from_file_location(
            pkg_name,
            str(init_file),
            submodule_search_locations=[str(pkg_dir)],
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[pkg_name] = module
            spec.loader.exec_module(module)
            return
    module = types.ModuleType(pkg_name)
    module.__path__ = [str(pkg_dir)]
    module.__package__ = pkg_name
    sys.modules[pkg_name] = module


def bootstrap_services() -> None:
    """Wire pipeline imports and namespace packages for all 6 Python services."""
    for path in (str(SERVICES_ROOT), str(PIPELINE_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)

    if "mnemos_services" not in sys.modules:
        root_pkg = types.ModuleType("mnemos_services")
        root_pkg.__path__ = [str(SERVICES_ROOT)]
        root_pkg.__package__ = "mnemos_services"
        sys.modules["mnemos_services"] = root_pkg

    for alias, folder_name in SERVICE_ALIASES.items():
        pkg_dir = SERVICES_ROOT / folder_name
        if pkg_dir.exists():
            _register_namespace(f"mnemos_services.{alias}", pkg_dir)


bootstrap_services()
