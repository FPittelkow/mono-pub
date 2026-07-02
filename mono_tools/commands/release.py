from pathlib import Path
import frontmatter
import typer
from mono_tools.config import load_config

app = typer.Typer()

BUILD_FIELDS = {
    "release",
    "validate",
    "draft_only",
}

@app.command()
def post():
    config = load_config()
    release_files(Path(config["drafts_path"]["posts"]), Path(config["releases_path"]["posts"]))

@app.command()
def project():
    config = load_config()
    release_files(Path(config["drafts_path"]["projects"]), Path(config["releases_path"]["projects"]))

@app.command()
def posts():
    post()

@app.command()
def projects():
    project()

def release_files(drafts_dir: Path, releases_dir: Path):
    drafts = list(drafts_dir.glob("*.md"))
    marked = [path for path in drafts if is_marked_for_release(path)]

    if not marked:
        typer.echo("No drafts for release.")
        return

    for path in marked:
        release_draft(path, releases_dir)

def is_marked_for_release(path: Path) -> bool:
    post = frontmatter.load(path)
    return post.metadata.get("release") is True

def validate_draft(post: frontmatter.Post, path: Path) -> bool:
    required = ["title", "date", "author"]
    missing = [key for key in required if key not in post.metadata]

    if missing:
        typer.echo(f"Missing {missing}: {path}")
        return False

    return True

def remove_build_fields(post: frontmatter.Post):
    for field in BUILD_FIELDS:
        post.metadata.pop(field, None)

def normalize_frontmatter(post: frontmatter.Post):
    #Convert the frontmatter to lowercase except the title
    pass

def consolidate_images():
    # move the linked images from the drafts folder to a subfolder named with the slug in the assets_path for post or projects respectively.
    pass

def replace_image_path():
    #replace the standard Markdown image path ( ![]() ) with the new path from consolidate_mages()
    #with {% picture default image_path] alt="" %}
    pass

def compile_draft(post: frontmatter.Post) -> frontmatter.Post:
    remove_build_fields(post)
    normalize_frontmatter(post)
    consolidate_images()
    replace_image_path()
    return post

def release_draft(path: Path, target_dir: Path):
    post = frontmatter.load(path)

    if not validate_draft(post, path):
        raise typer.Exit(1)

    compiled = compile_draft(post)

    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / path.name

    if target.exists():
        typer.echo(f"Draft {target} already exists.")
        raise typer.Exit(1)

    target.write_text(frontmatter.dumps(compiled), encoding="utf-8")
    path.unlink()

    typer.echo(f"Draft {target} released.")
