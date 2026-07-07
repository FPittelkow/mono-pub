from pathlib import Path
import shlex
import subprocess

import typer

from mono_pub.config import load_config
from mono_pub.process.release_config import PATH_KEYS_BY_TYPE

app = typer.Typer()


@app.command()
def post():
    open_draft_path("post")


@app.command()
def project():
    open_draft_path("project")


@app.command()
def music():
    open_draft_path("music")


def open_draft_path(content_type: str):
    config = load_config()
    editor_command = config.get("editor_command")

    if not editor_command:
        typer.echo("Missing editor_command in configuration.")
        raise typer.Exit(1)

    path_key = PATH_KEYS_BY_TYPE[content_type]
    draft_path = Path(config["drafts_path"][path_key])

    if not draft_path.exists():
        typer.echo(f"Draft path does not exist: {draft_path}")
        raise typer.Exit(1)

    command = build_editor_command(editor_command, draft_path)

    try:
        subprocess.run(command, check=True)
    except FileNotFoundError:
        typer.echo(f"Editor command not found: {command[0]}")
        raise typer.Exit(1)
    except subprocess.CalledProcessError as error:
        typer.echo(f"Could not open {draft_path}: {' '.join(command)}")
        if error.output:
            typer.echo(error.output)
        raise typer.Exit(1)

    typer.echo(f"Opened: {draft_path}")


def build_editor_command(editor_command: str, draft_path: Path) -> list[str]:
    command = shlex.split(editor_command)

    if not command:
        raise ValueError("editor_command cannot be empty")

    draft_path_value = str(draft_path)

    if any("{path}" in part for part in command):
        return [part.replace("{path}", draft_path_value) for part in command]

    return [*command, draft_path_value]
