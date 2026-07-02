from pathlib import Path

import typer

from mono_tools.config import load_config
from mono_tools.process.release_config import PATH_KEYS_BY_TYPE

app = typer.Typer()
draft_app = typer.Typer()
release_app = typer.Typer()

app.add_typer(draft_app, name="draft")
app.add_typer(release_app, name="release")


@app.callback(invoke_without_command=True)
def list_all(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        list_group("draft", "drafts_path")
        list_group("release", "releases_path")


@draft_app.callback(invoke_without_command=True)
def list_drafts(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        list_group("draft", "drafts_path")


@release_app.callback(invoke_without_command=True)
def list_releases(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        list_group("release", "releases_path")


@draft_app.command()
def post():
    list_content_type("draft", "drafts_path", "post")


@draft_app.command()
def project():
    list_content_type("draft", "drafts_path", "project")


@draft_app.command()
def music():
    list_content_type("draft", "drafts_path", "music")


@release_app.command()
def post():
    list_content_type("release", "releases_path", "post")


@release_app.command()
def project():
    list_content_type("release", "releases_path", "project")


@release_app.command()
def music():
    list_content_type("release", "releases_path", "music")


def list_group(label: str, config_key: str):
    for content_type in PATH_KEYS_BY_TYPE:
        list_content_type(label, config_key, content_type)


def list_content_type(label: str, config_key: str, content_type: str):
    config = load_config()
    path_key = PATH_KEYS_BY_TYPE[content_type]
    path = Path(config[config_key][path_key])
    files = sorted(path.glob("*.md"))

    typer.echo(f"{label.capitalize()} {content_type}: {len(files)}")
    for file in files:
        typer.echo(f"  {file.name}")
