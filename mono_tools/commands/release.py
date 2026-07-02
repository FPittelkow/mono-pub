from pathlib import Path
import re
import shutil

import frontmatter
import typer
from slugify import slugify

from mono_tools.config import load_config

app = typer.Typer()

IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
FRONTMATTER_IMAGE_FIELDS = {"image_preview"}
CATEGORY_FIELDS = {"categories"}
PRESERVE_STRING_FIELDS = {"title", "short_description", *FRONTMATTER_IMAGE_FIELDS}

BUILD_FIELDS = {
    "release",
    "validate",
    "draft_only",
}

@app.command()
def post():
    config = load_config()
    release_files(
        Path(config["drafts_path"]["posts"]),
        Path(config["releases_path"]["posts"]),
        Path(config["assets_path"]["posts"]),
    )

@app.command()
def project():
    config = load_config()
    release_files(
        Path(config["drafts_path"]["projects"]),
        Path(config["releases_path"]["projects"]),
        Path(config["assets_path"]["projects"]),
    )

@app.command()
def posts():
    post()

@app.command()
def projects():
    project()

def release_files(drafts_dir: Path, releases_dir: Path, assets_dir: Path):
    drafts = list(drafts_dir.glob("*.md"))
    marked = [path for path in drafts if is_marked_for_release(path)]

    if not marked:
        typer.echo("No drafts for release.")
        return

    for path in marked:
        release_draft(path, releases_dir, assets_dir)

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
    normalized = {}

    for key, value in post.metadata.items():
        normalized[key.lower()] = normalize_frontmatter_value(key, value)

    post.metadata = normalized

def normalize_frontmatter_value(key: str, value):
    if key.lower() in PRESERVE_STRING_FIELDS:
        return value

    if key.lower() in CATEGORY_FIELDS:
        return normalize_category_value(value)

    if isinstance(value, str):
        return value.lower()

    if isinstance(value, list):
        return [normalize_frontmatter_value(key, item) for item in value]

    if isinstance(value, dict):
        return {
            nested_key.lower(): normalize_frontmatter_value(nested_key, nested_value)
            for nested_key, nested_value in value.items()
        }

    return value

def normalize_category_value(value):
    if isinstance(value, str):
        value = value.strip().lower()
        return value[:1].upper() + value[1:]

    if isinstance(value, list):
        return [normalize_category_value(item) for item in value]

    return value

def consolidate_images(post: frontmatter.Post, draft_path: Path, assets_dir: Path) -> dict[str, str]:
    slug = slugify(post.metadata["title"])
    target_dir = assets_dir / slug
    replacements = {}

    for _, image_path in IMAGE_PATTERN.findall(post.content):
        replacement = consolidate_image(image_path, draft_path, target_dir, slug)
        if replacement is not None:
            replacements[image_path] = replacement

    for field in FRONTMATTER_IMAGE_FIELDS:
        image_path = post.metadata.get(field)
        if not isinstance(image_path, str):
            continue

        replacement = consolidate_image(image_path, draft_path, target_dir, slug)
        if replacement is not None:
            post.metadata[field] = replacement

    return replacements

def consolidate_image(image_path: str, draft_path: Path, target_dir: Path, slug: str) -> str | None:
    source_path = resolve_image_path(image_path, draft_path)
    if source_path is None:
        return None

    if not source_path.exists():
        typer.echo(f"Image not found: {source_path}")
        raise typer.Exit(1)

    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source_path.name
    shutil.copy2(source_path, target)
    return f"assets/{slug}/{target.name}"

def resolve_image_path(image_path: str, draft_path: Path) -> Path | None:
    if not image_path.strip():
        return None

    if is_external_or_site_path(image_path):
        return None

    path = Path(image_path)
    if path.is_absolute():
        return path

    return draft_path.parent / path

def is_external_or_site_path(image_path: str) -> bool:
    return (
        image_path.startswith("/")
        or image_path.startswith("#")
        or "://" in image_path
        or image_path.startswith("mailto:")
    )

def replace_image_path(post: frontmatter.Post, replacements: dict[str, str]):
    def replace(match: re.Match) -> str:
        alt = match.group(1)
        image_path = match.group(2)
        replacement = replacements.get(image_path)

        if replacement is None:
            return match.group(0)

        return f'{{% picture default {replacement} alt="{alt}" %}}'

    post.content = IMAGE_PATTERN.sub(replace, post.content)

def compile_draft(post: frontmatter.Post, draft_path: Path, assets_dir: Path) -> frontmatter.Post:
    remove_build_fields(post)
    normalize_frontmatter(post)
    replacements = consolidate_images(post, draft_path, assets_dir)
    replace_image_path(post, replacements)
    return post

def release_draft(path: Path, target_dir: Path, assets_dir: Path):
    post = frontmatter.load(path)

    if not validate_draft(post, path):
        raise typer.Exit(1)

    compiled = compile_draft(post, path, assets_dir)

    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / path.name

    if target.exists():
        typer.echo(f"Draft {target} already exists.")
        raise typer.Exit(1)

    target.write_text(frontmatter.dumps(compiled), encoding="utf-8")
    path.unlink()

    typer.echo(f"Draft {target} released.")
