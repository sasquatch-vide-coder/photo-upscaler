"""CLI command: upscale a single image."""

import click
from tqdm import tqdm

from upscaler.core.config import settings
from upscaler.core.progress import EventType, ProgressEvent, ProgressReporter
from upscaler.core.model_manager import ModelManager
from upscaler.core.upscale_engine import UpscaleEngine


@click.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.argument("output_path", required=False, type=click.Path())
@click.option("-m", "--model", "model_id", required=True, help="Model ID (filename without extension)")
@click.option("-s", "--scale", type=int, default=None, help="Scale factor (2, 4, 8)")
@click.option("-f", "--format", "output_format", default=None, help="Output format (png, jpg, webp)")
@click.option("--tile-size", type=int, default=None, help="Tile size for processing")
@click.option("--fp32", is_flag=True, help="Disable fp16 (use fp32)")
@click.option("-q", "--quality", type=int, default=None, help="JPEG/WebP quality (1-100)")
def upscale(input_path, output_path, model_id, scale, output_format, tile_size, fp32, quality):
    """Upscale a single image using an AI model."""
    if fp32:
        settings.fp16 = False

    progress = ProgressReporter()
    pbar = None

    def on_progress(event: ProgressEvent):
        nonlocal pbar
        if event.event_type == EventType.TILE_PROGRESS:
            total = event.data.get("tiles_total", 0)
            done = event.data.get("tiles_done", 0)
            pass_num = event.data.get("pass_num", 1)
            total_passes = event.data.get("total_passes", 1)
            desc = f"Pass {pass_num}/{total_passes}" if total_passes > 1 else "Upscaling"
            if pbar is None:
                pbar = tqdm(total=total, desc=desc, unit="tile")
            elif pbar.total != total:
                pbar.reset(total=total)
                pbar.set_description(desc)
            pbar.n = done
            pbar.refresh()
        elif event.event_type == EventType.MODEL_LOADING:
            click.echo(f"Loading model: {event.data.get('model_id')}...")
        elif event.event_type == EventType.IMAGE_COMPLETE:
            if pbar:
                pbar.close()
            click.echo(f"Saved: {event.data.get('output_path')}")

    progress.add_callback(on_progress)

    manager = ModelManager(progress=progress)
    manager.scan()

    engine = UpscaleEngine(model_manager=manager, progress=progress)

    try:
        engine.upscale(
            input_path=input_path,
            output_path=output_path,
            model_id=model_id,
            scale=scale,
            output_format=output_format,
            tile_size=tile_size,
            jpeg_quality=quality,
        )
    except KeyError as e:
        click.echo(f"Error: {e}", err=True)
        available = [m.model_id for m in manager.list_models()]
        if available:
            click.echo(f"Available models: {', '.join(available)}", err=True)
        else:
            click.echo("No models found. Run: upscaler models download --all", err=True)
        raise SystemExit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
