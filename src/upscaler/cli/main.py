"""CLI entry point — Click command group."""

import click

from upscaler.cli.commands.upscale_cmd import upscale
from upscaler.cli.commands.batch_cmd import batch
from upscaler.cli.commands.compare_cmd import compare
from upscaler.cli.commands.models_cmd import models
from upscaler.cli.commands.serve_cmd import serve


@click.group()
@click.version_option(package_name="photo-upscaler")
def cli():
    """Photo Upscaler — Local AI image upscaling with multi-model comparison."""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )


cli.add_command(upscale)
cli.add_command(batch)
cli.add_command(compare)
cli.add_command(models)
cli.add_command(serve)
