"""
Plugin registry for custom validators.

Register plugins at import time or load from entry points in future releases.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from app.schemas import ValidationFinding


@dataclass
class ValidatorPlugin(ABC):
    """Base class for pluggable validators."""

    name: str
    version: str = "1.0.0"
    supported_types: list[str] = field(default_factory=lambda: ["yaml", "terraform"])

    @abstractmethod
    def validate(self, content: str, file_path: str, file_type: str) -> list[ValidationFinding]:
        """Run plugin validation and return findings."""


class PluginRegistry:
    """Central registry of validator plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, ValidatorPlugin] = {}

    def register(self, plugin: ValidatorPlugin) -> None:
        if plugin.name in self._plugins:
            raise ValueError(f"Plugin already registered: {plugin.name}")
        self._plugins[plugin.name] = plugin

    def unregister(self, name: str) -> None:
        self._plugins.pop(name, None)

    def list_plugins(self) -> list[dict[str, Any]]:
        return [
            {"name": p.name, "version": p.version, "supported_types": p.supported_types}
            for p in self._plugins.values()
        ]

    def run_all(
        self,
        content: str,
        file_path: str,
        file_type: str,
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for plugin in self._plugins.values():
            if file_type in plugin.supported_types or "auto" in plugin.supported_types:
                findings.extend(plugin.validate(content, file_path, file_type))
        return findings


@lru_cache
def get_plugin_registry() -> PluginRegistry:
    return PluginRegistry()
