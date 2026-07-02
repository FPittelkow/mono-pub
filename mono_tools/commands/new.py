import typer

from datetime import date
from pathlib import Path

from slugify import slugify
from jinja2 import Environment, FileSystemLoader

from mono_tools.config import load_config
config = load_config()

app = typer.Typer()

@app.command()
def post(title: str):
    create_post(title)

@app.command()
def project(title: str):
    create_project(title)

def file_operation(title: str, path: Path, template: str):
    today = date.today()
    slug = slugify(title)

    filename = f"{today.isoformat()}-{slug}.md"
    path.mkdir(parents=True, exist_ok=True)

    target = path / filename

    if target.exists():
        typer.echo(f"Exists already: {target}")
        raise typer.Exit(1)

    env = Environment(loader=FileSystemLoader(config["templates_path"]))
    template = env.get_template(template)

    content = template.render(
        title=title,
        date=today.isoformat(),
        author=config["author"]
    )

    target.write_text(content, encoding="utf-8")
    typer.echo(f"Created: {target}")

def create_post(title: str):
    file_operation(title, Path(config["drafts_path"]["posts"]), "post.md.j2")

def create_project(title: str):
    file_operation(title, Path(config["drafts_path"]["project"]), "project.md.j2")