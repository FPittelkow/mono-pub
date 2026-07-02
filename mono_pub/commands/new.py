import typer

from datetime import date
from pathlib import Path

from slugify import slugify
from jinja2 import Environment, FileSystemLoader

from mono_pub.config import load_config
config = load_config()

app = typer.Typer()

@app.command()
def post(title: str):
    create_post(title)

@app.command()
def project(title: str):
    create_project(title)

@app.command()
def music(title: str):
    create_music(title)

def file_operation(title: str, path: Path, content_type: str):
    today = date.today()
    slug = slugify(title)

    filename = f"{today.isoformat()}-{slug}.md"
    path.mkdir(parents=True, exist_ok=True)

    target = path / filename

    if target.exists():
        typer.echo(f"Exists already: {target}")
        raise typer.Exit(1)

    env = Environment(loader=FileSystemLoader(config["templates_path"]))
    template = env.get_template(f"{content_type}.md.j2")

    template_context = {
        "title": title,
        "date": today.isoformat(),
        "author": config["author"],
        "type": content_type,
    }

    if content_type == "music":
        template_context["permalink"] = slug

    content = template.render(
        **template_context
    )

    target.write_text(content, encoding="utf-8")
    typer.echo(f"Created: {target}")

def create_post(title: str):
    file_operation(title, Path(config["drafts_path"]["posts"]), "post")

def create_project(title: str):
    file_operation(title, Path(config["drafts_path"]["projects"]), "project")

def create_music(title: str):
    file_operation(title, Path(config["drafts_path"]["music"]), "music")
