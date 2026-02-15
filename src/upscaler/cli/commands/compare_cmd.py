"""CLI command: compare multiple models on one image."""

import click
from rich.console import Console
from rich.table import Table
from tqdm import tqdm

from upscaler.core.config import settings
from upscaler.core.progress import EventType, ProgressEvent, ProgressReporter
from upscaler.core.model_manager import ModelManager
from upscaler.core.comparison import ComparisonRunner

console = Console()


@click.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("-m", "--models", "model_ids", required=True, help="Comma-separated model IDs")
@click.option("-s", "--scale", type=int, default=None, help="Scale factor")
@click.option("-o", "--output-dir", type=click.Path(), default=None, help="Output directory")
@click.option("-f", "--format", "output_format", default=None, help="Output format")
@click.option("--tile-size", type=int, default=None, help="Tile size")
@click.option("-q", "--quality", type=int, default=None, help="JPEG/WebP quality")
def compare(input_path, model_ids, scale, output_dir, output_format, tile_size, quality):
    """Compare multiple models on a single image."""
    models_list = [m.strip() for m in model_ids.split(",")]

    progress = ProgressReporter()
    current_model = None
    pbar = None

    def on_progress(event: ProgressEvent):
        nonlocal current_model, pbar
        if event.event_type == EventType.COMPARISON_MODEL_START:
            mid = event.data.get("model_id", "")
            current_model = mid
            click.echo(f"\nProcessing: {mid}")
            pbar = None
        elif event.event_type == EventType.TILE_PROGRESS:
            total = event.data.get("tiles_total", 0)
            done = event.data.get("tiles_done", 0)
            if pbar is None:
                pbar = tqdm(total=total, desc=f"  {current_model}", unit="tile")
            pbar.n = done
            pbar.refresh()
        elif event.event_type == EventType.COMPARISON_MODEL_DONE:
            if pbar:
                pbar.close()
                pbar = None
        elif event.event_type == EventType.MODEL_LOADING:
            click.echo(f"  Loading model: {event.data.get('model_id')}...")

    progress.add_callback(on_progress)

    manager = ModelManager(progress=progress)
    manager.scan()
    runner = ComparisonRunner(model_manager=manager, progress=progress)

    result = runner.compare(
        input_path=input_path,
        model_ids=models_list,
        scale=scale,
        output_dir=output_dir,
        output_format=output_format,
        tile_size=tile_size,
        jpeg_quality=quality,
    )

    # Print summary table
    table = Table(title="\nComparison Results")
    table.add_column("Model", style="cyan")
    table.add_column("Time", justify="right")
    table.add_column("Status")
    table.add_column("Output")

    for r in result.results:
        status = "[green]OK[/green]" if r.success else f"[red]FAILED: {r.error}[/red]"
        table.add_row(r.model_id, f"{r.duration_seconds:.1f}s", status, r.output_path)

    console.print(table)
