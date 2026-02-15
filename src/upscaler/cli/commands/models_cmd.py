"""CLI command: manage models — list, download, info."""

import click
from rich.console import Console
from rich.table import Table
from tqdm import tqdm

from upscaler.core.config import settings
from upscaler.core.model_manager import ModelManager
from upscaler.core.model_registry import (
    download_model,
    list_available,
    list_not_downloaded,
    get_entry,
)
from upscaler.core.progress import EventType, ProgressEvent, ProgressReporter

console = Console()


@click.group()
def models():
    """Manage upscaling models."""
    pass


@models.command("list")
@click.option("--available", is_flag=True, help="Show downloadable models from registry")
def list_models(available):
    """List installed or available models."""
    if available:
        entries = list_available()
        table = Table(title="Available Models (Registry)")
        table.add_column("Key", style="cyan")
        table.add_column("Name")
        table.add_column("Arch", style="green")
        table.add_column("Scale", justify="right")

        not_dl = {e.key for e in list_not_downloaded()}
        for entry in entries:
            status = "[red]not downloaded[/red]" if entry.key in not_dl else "[green]installed[/green]"
            table.add_row(entry.key, entry.name, entry.architecture, f"{entry.scale}x", status)

        # Add status column
        table.add_column("Status")
        # Re-create with all columns
        table2 = Table(title="Available Models (Registry)")
        table2.add_column("Key", style="cyan")
        table2.add_column("Name")
        table2.add_column("Arch", style="green")
        table2.add_column("Scale", justify="right")
        table2.add_column("Status")
        for entry in entries:
            status = "not downloaded" if entry.key in not_dl else "installed"
            style = "red" if entry.key in not_dl else "green"
            table2.add_row(entry.key, entry.name, entry.architecture, f"{entry.scale}x", f"[{style}]{status}[/{style}]")

        console.print(table2)
    else:
        manager = ModelManager()
        models_list = manager.scan()

        if not models_list:
            click.echo("No models found. Run: upscaler models download --all")
            return

        table = Table(title="Installed Models")
        table.add_column("ID", style="cyan")
        table.add_column("Architecture", style="green")
        table.add_column("Scale", justify="right")
        table.add_column("Size (MB)", justify="right")

        for m in models_list:
            table.add_row(m.model_id, m.architecture, f"{m.scale}x", f"{m.file_size_mb:.1f}")

        console.print(table)


@models.command("download")
@click.argument("model_key", required=False)
@click.option("--all", "download_all", is_flag=True, help="Download all registry models")
def download(model_key, download_all):
    """Download a model from the registry."""
    progress = ProgressReporter()
    pbar = None

    def on_progress(event: ProgressEvent):
        nonlocal pbar
        if event.event_type == EventType.DOWNLOAD_PROGRESS:
            total = event.data.get("total", 0)
            downloaded = event.data.get("downloaded", 0)
            if pbar is None and total > 0:
                pbar = tqdm(total=total, unit="B", unit_scale=True, desc=event.data.get("model_key", ""))
            if pbar:
                pbar.n = downloaded
                pbar.refresh()

    progress.add_callback(on_progress)

    if download_all:
        entries = list_not_downloaded()
        if not entries:
            click.echo("All registry models are already downloaded.")
            return
        for entry in entries:
            pbar = None
            click.echo(f"\nDownloading {entry.name}...")
            download_model(entry.key, progress=progress)
            if pbar:
                pbar.close()
        click.echo("\nAll models downloaded.")
    elif model_key:
        entry = get_entry(model_key)
        if not entry:
            click.echo(f"Unknown model key: {model_key}", err=True)
            click.echo("Available keys:", err=True)
            for e in list_available():
                click.echo(f"  {e.key}", err=True)
            raise SystemExit(1)
        click.echo(f"Downloading {entry.name}...")
        download_model(model_key, progress=progress)
        if pbar:
            pbar.close()
        click.echo("Done.")
    else:
        click.echo("Specify a model key or use --all. See: upscaler models list --available")


@models.command("info")
@click.argument("model_id")
def info(model_id):
    """Show detailed info about an installed model."""
    manager = ModelManager()
    manager.scan()
    model_info = manager.get_model_info(model_id)

    if not model_info:
        click.echo(f"Model not found: {model_id}", err=True)
        raise SystemExit(1)

    console.print(f"[cyan]Model:[/cyan] {model_info.model_id}")
    console.print(f"[cyan]File:[/cyan] {model_info.filename}")
    console.print(f"[cyan]Architecture:[/cyan] {model_info.architecture}")
    console.print(f"[cyan]Scale:[/cyan] {model_info.scale}x")
    console.print(f"[cyan]Input Channels:[/cyan] {model_info.input_channels}")
    console.print(f"[cyan]Size:[/cyan] {model_info.file_size_mb:.1f} MB")
