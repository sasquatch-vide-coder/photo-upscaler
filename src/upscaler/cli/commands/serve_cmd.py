"""CLI command: launch the web server."""

import click

from upscaler.core.config import settings


@click.command()
@click.option("--host", default=None, help="Bind address")
@click.option("--port", type=int, default=None, help="Port number")
@click.option("--no-browser", is_flag=True, help="Don't auto-open browser")
def serve(host, port, no_browser):
    """Launch the web UI server."""
    import uvicorn

    host = host or settings.host
    port = port or settings.port

    if not no_browser and settings.open_browser:
        import webbrowser
        import threading
        def open_browser():
            import time
            time.sleep(1.5)
            webbrowser.open(f"http://{host}:{port}")
        threading.Thread(target=open_browser, daemon=True).start()

    click.echo(f"Starting server at http://{host}:{port}")
    uvicorn.run(
        "upscaler.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        log_level="info",
    )
