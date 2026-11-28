"""Mastery-only plugin command.

The plugin package layer (install/approve/rollback/catalog) was removed by the
cleanup. ``deeptutor plugin list`` remains a contract gate, so this module now
reports the single registered capability and its fixed tool surface directly
from the runtime registries, without importing ``deeptutor.plugins``.
"""

from __future__ import annotations

from dataclasses import asdict
import json

from rich.console import Console
from rich.table import Table
import typer

console = Console()


def register(app: typer.Typer) -> None:
    @app.command("list")
    def plugin_list() -> None:
        """List the registered mastery capability and its tools."""
        from deeptutor.runtime.registry.capability_registry import get_capability_registry
        from deeptutor.runtime.registry.tool_registry import get_tool_registry

        table = Table(title="Registered mastery surface")
        table.add_column("Name", style="bold")
        table.add_column("Type")
        table.add_column("Status")
        table.add_column("Description")

        for definition in get_tool_registry().get_definitions():
            table.add_row(definition.name, "tool", "enabled", definition.description[:80])

        for manifest in get_capability_registry().get_manifests():
            table.add_row(
                manifest["name"],
                "capability",
                "enabled",
                manifest["description"][:80],
            )
        console.print(table)

    @app.command("info")
    def plugin_info(
        name: str = typer.Argument(..., help="Registered tool or capability name."),
    ) -> None:
        """Show details of a registered tool or capability."""
        from deeptutor.runtime.registry.capability_registry import get_capability_registry
        from deeptutor.runtime.registry.tool_registry import get_tool_registry

        tool = get_tool_registry().get(name)
        if tool:
            console.print_json(json.dumps(tool.get_definition().to_openai_schema(), indent=2))
            return

        capability = get_capability_registry().get(name)
        if capability:
            from deeptutor.app import DeepTutorApp

            availability = DeepTutorApp().get_capability_availability(name)
            console.print_json(
                json.dumps(
                    {
                        "name": capability.manifest.name,
                        "description": capability.manifest.description,
                        "cli_aliases": capability.manifest.cli_aliases,
                        "stages": capability.manifest.stages,
                        "tools_used": capability.manifest.tools_used,
                        "config_defaults": capability.manifest.config_defaults,
                        "availability": asdict(availability),
                    },
                    indent=2,
                )
            )
            return

        console.print(f"[red]'{name}' not found.[/]")
        raise typer.Exit(code=1)
