from pathlib import Path

import typer

from mono_pub.config import load_config
from mono_pub.process.assets import MissingImageError
from mono_pub.process.release import (
    ExistingReleaseError,
    MissingRequiredFieldsError,
    release_type,
)

app = typer.Typer()


@app.command()
def post():
    release_content_type("post")


@app.command()
def project():
    release_content_type("project")


@app.command()
def music():
    release_content_type("music")


@app.command()
def posts():
    post()


@app.command()
def projects():
    project()


@app.command()
def musics():
    music()

@app.command()
def all():
    post()
    project()
    music()

def release_content_type(content_type: str):
    config = load_config()

    try:
        released = release_type(config, content_type)
    except MissingRequiredFieldsError as error:
        typer.echo(f"Missing {error.fields}: {error.path}")
        raise typer.Exit(1)
    except ExistingReleaseError as error:
        typer.echo(f"Draft {error.path} already exists.")
        raise typer.Exit(1)
    except MissingImageError as error:
        typer.echo(f"Image not found: {error.path}")
        raise typer.Exit(1)

    if not released:
        typer.echo("No drafts for release.")
        return

    for path in released:
        typer.echo(f"Draft {Path(path)} released.")
