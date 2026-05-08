import typer
import uvicorn

from config import settings

app = typer.Typer(
    name="voiceagent",
    help="VoiceAgent CLI - Real-time voice agent backend",
    add_completion=False,
)


@app.command()
def serve(
    host: str = typer.Option(settings.HOST, "--host", "-h", help="Host to bind"),
    port: int = typer.Option(settings.PORT, "--port", "-p", help="Port to bind"),
    reload: bool = typer.Option(settings.RELOAD, "--reload", "-r", help="Enable auto-reload"),
    workers: int = typer.Option(settings.WORKERS, "--workers", "-w", help="Number of workers"),
):
    """Start the VoiceAgent server."""
    typer.echo(f"Starting VoiceAgent on {host}:{port}")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers if not reload else 1,
    )


@app.command()
def dev():
    """Start the server in development mode."""
    typer.echo("Starting VoiceAgent in development mode...")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


@app.command()
def version():
    """Show version information."""
    typer.echo(f"VoiceAgent v{settings.APP_VERSION}")
    typer.echo(f"Environment: {settings.ENVIRONMENT}")


if __name__ == "__main__":
    app()
