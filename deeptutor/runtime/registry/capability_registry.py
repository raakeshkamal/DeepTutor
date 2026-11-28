"""Compatibility view of turn capabilities backed by CapabilityCatalog."""

from __future__ import annotations

import importlib
import inspect
import logging
from typing import Any
import warnings

from pydantic import BaseModel

from deeptutor.core.capability_protocol import TurnCapability
from deeptutor.i18n.metadata_i18n import capability_description_i18n
from deeptutor.modules.catalog import contribution_enabled
def load_entry_point_group(group, coerce, log=None):
    """Mastery-only: the plugin layer is gone, so no external capabilities load."""
    return []
from deeptutor.runtime.bootstrap.builtin_capabilities import BUILTIN_CAPABILITY_SPECS
from deeptutor.runtime.capability_catalog import (
    CapabilityCatalog,
    EmptyConfig,
    get_capability_catalog,
)
from deeptutor.runtime.request_contracts import CAPABILITY_CONFIG_MODELS

logger = logging.getLogger(__name__)

EXTENSIONS_GROUP = "deeptutor.extensions"
LEGACY_PLUGINS_GROUP = "deeptutor.plugins"


def _import_capability_class(path: str) -> type[TurnCapability]:
    module_path, class_name = path.rsplit(":", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _turn_factory(loaded: object) -> tuple[TurnCapability, type[TurnCapability]] | None:
    obj: Any = loaded
    if inspect.isclass(obj):
        instance = obj()
        factory = obj
    elif callable(obj) and not isinstance(obj, TurnCapability):
        produced = obj()
        if inspect.isclass(produced):
            instance = produced()
            factory = produced
        else:
            instance = produced
            factory = obj
    else:
        instance = obj
        factory = type(obj)
    if not isinstance(instance, TurnCapability):
        return None
    return instance, factory


class CapabilityRegistry:
    """Legacy turn-only registry facade; every ``get`` creates an instance."""

    def __init__(self, catalog: CapabilityCatalog | None = None) -> None:
        self.catalog = catalog if catalog is not None else CapabilityCatalog()

    def register(
        self,
        capability: TurnCapability | type[TurnCapability] | Any,
        *,
        config_model: type[BaseModel] | None = None,
    ) -> None:
        resolved = _turn_factory(capability)
        if resolved is None:
            raise TypeError("Expected a TurnCapability class, factory, or instance")
        instance, factory = resolved
        model = config_model or CAPABILITY_CONFIG_MODELS.get(instance.name, EmptyConfig)
        self.catalog.register(
            name=instance.name,
            kind="turn",
            manifest=instance.manifest,
            factory=factory,
            config_model=model,
            replace=True,
        )
        logger.debug("Registered turn capability factory: %s", instance.name)

    def load_builtins(self) -> None:
        for name, spec in BUILTIN_CAPABILITY_SPECS.items():
            if not contribution_enabled("capabilities", name):
                continue
            if self.catalog.get("turn", name) is not None:
                continue
            class_path = spec.class_path

            def _factory(path: str = class_path) -> TurnCapability:
                return _import_capability_class(path)()

            self.catalog.register(
                name=name,
                kind="turn",
                manifest=spec.manifest,
                factory=_factory,
                config_model=CAPABILITY_CONFIG_MODELS[name],
            )
            logger.debug("Registered lazy built-in turn capability: %s", name)

    def load_plugins(self) -> None:
        """Load the canonical extension group, then the one-version legacy group."""

        def _accept(ep_name: str, loaded: object) -> str | None:
            resolved = _turn_factory(loaded)
            if resolved is None:
                return None
            instance, _factory = resolved
            existing = self.catalog.get("turn", instance.name)
            if (
                existing is not None
                and getattr(existing.factory, "_plugin_allowed", lambda: True)()
            ):
                logger.warning("Turn extension %s is already registered; ignoring", ep_name)
                return None
            self.register(loaded)
            return instance.name

        load_entry_point_group(EXTENSIONS_GROUP, _accept, log=logger)

        # Mastery-only: the legacy plugin loader was removed with the plugin
        # package. Only manifest-declared capabilities are registered.

    def get(self, name: str) -> TurnCapability | None:
        if not contribution_enabled("capabilities", name):
            return None
        # Mastery-only: no plugin packages add capabilities at runtime.
        if name not in BUILTIN_CAPABILITY_SPECS:
            return None
        entry = self.catalog.get("turn", name)
        if entry is not None and not getattr(entry.factory, "_plugin_allowed", lambda: True)():
            return None
        capability = self.catalog.create("turn", name)
        return capability if isinstance(capability, TurnCapability) else None

    def list_capabilities(self) -> list[str]:
        return [manifest["name"] for manifest in self.get_manifests()]

    def get_manifests(self) -> list[dict[str, Any]]:
        manifests = [
            {
                "name": entry.name,
                "kind": entry.kind,
                "description": entry.manifest.description,
                "description_i18n": capability_description_i18n(
                    entry.name,
                    entry.manifest.description,
                ),
                "stages": entry.manifest.stages,
                "tools_used": entry.manifest.tools_used,
                "cli_aliases": entry.manifest.cli_aliases,
                "request_schema": entry.config_model.model_json_schema(mode="validation"),
                "config_defaults": entry.manifest.config_defaults,
            }
            for entry in self.catalog.entries("turn")
            if contribution_enabled("capabilities", entry.name)
            and getattr(entry.factory, "_plugin_allowed", lambda: True)()
        ]
        return manifests


_default_registry: CapabilityRegistry | None = None


def get_capability_registry() -> CapabilityRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = CapabilityRegistry(get_capability_catalog())
        _default_registry.load_builtins()
        _default_registry.load_plugins()
    return _default_registry


__all__ = [
    "CapabilityRegistry",
    "EXTENSIONS_GROUP",
    "get_capability_registry",
]
