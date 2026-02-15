"""CLI command: batch process a folder of images."""

import click
from tqdm import tqdm

from upscaler.core.config import settings
from upscaler.core.progress import EventType, ProgressEvent, ProgressReporter
from upscaler.core.model_manager import ModelManager
from upscaler.core.upscale_engine import UpscaleEngine
from upscaler.core.batch import run_batch


@click.command()
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False))
@click.argument("output_dir", required=False, type=click.Path())
@click.option("-m", "--model", "model_id", required=True, help="Model ID")
@click.option("-s", "--scale", type=int, default=None, help="Scale factor")
@click.option("-f", "--format", "output_format", default=None, help="Output format")
@click.option("--recursive", is_flag=True, help="Process subdirectories")
@click.option("--skip-existing", is_flag=True, help="Skip already processed files")
@click.option("--tile-size", type=int, default=None, help="Tile size")
@click.option("-q", "--quality", type=int, default=None, help="JPEG/WebP quality")
def batch(input_dir, output_dir, model_id, scale, output_format, recursive, skip_existing, tile_size, quality):
    """Batch upscale all images in a directory."""
    progress = ProgressReporter()
    pbar = None

    def on_progress(event: ProgressEvent):
        nonlocal pbar
        if event.event_type == EventType.BATCH_PROGRESS:
            total = event.data.get("total", 0)
            completed = event.data.get("completed", 0)
            current = event.data.get("current_file", "")
            if pbar is None:
                pbar = tqdm(total=total, desc="Batch", unit="img")
            pbar.n = completed
            pbar.set_postfix(file=current)
            pbar.refresh()
        elif event.event_type == EventType.MODEL_LOADING:
            click.echo(f"Loading model: {event.data.get('model_id')}...")

    progress.add_callback(on_progress)

    manager = ModelManager(progress=progress)
    manager.scan()
    engine = UpscaleEngine(model_manager=manager, progress=progress)

    result = run_batch(
        engine=engine,
        input_dir=input_dir,
        output_dir=output_dir,
        model_id=model_id,
        scale=scale,
        output_format=output_format,
        recursive=recursive,
        skip_existing=skip_existing,
        tile_size=tile_size,
        jpeg_quality=quality,
        progress=progress,
    )

    if pbar:
        pbar.close()

    click.echo(f"\nBatch complete: {result.completed} processed, {result.skipped} skipped, {result.failed} failed")
    if result.errors:
        click.echo("Errors:")
        for err in result.errors:
            click.echo(f"  {err}")
