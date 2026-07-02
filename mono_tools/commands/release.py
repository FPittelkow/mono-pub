from pathlib import Path
import re
import shutil

import frontmatter
import typer
from slugify import slugify

from mono_tools.config import load_config

app = typer.Typer()

IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
DEFAULT_RELEASE_CONFIG = {
    "build_fields": ["release", "validate", "draft_only"],
    "frontmatter_image_fields": ["image_preview"],
    "category_fields": ["categories"],
    "preserve_string_fields": ["title", "short_description"],
    "required_fields": {
        "common": ["title", "date", "author"],
        "project": ["archive_record", "short_description"],
    },
}

PATH_KEYS_BY_TYPE = {
    "post": "posts",
    "project": "projects",
    "music": "music",
}

@app.command()
def post():
    release_type("post")

@app.command()
def project():
    release_type("project")

@app.command()
def music():
    release_type("music")

def release_type(content_type: str):
    config = load_config()
    path_key = PATH_KEYS_BY_TYPE[content_type]

    release_files(
        Path(config["drafts_path"][path_key]),
        Path(config["releases_path"][path_key]),
        Path(config["assets_path"][path_key]),
        release_config=get_release_config(config),
        content_type=content_type,
    )

@app.command()
def posts():
    post()

@app.command()
def projects():
    project()

@app.command()
def musics():
    music()

def get_release_config(config: dict) -> dict:
    release_config = DEFAULT_RELEASE_CONFIG | config.get("release", {})
    required_fields = DEFAULT_RELEASE_CONFIG["required_fields"] | release_config.get("required_fields", {})
    release_config["required_fields"] = required_fields
    release_config["build_fields"] = normalize_field_names(release_config["build_fields"])
    release_config["frontmatter_image_fields"] = normalize_field_names(
        release_config["frontmatter_image_fields"]
    )
    release_config["category_fields"] = normalize_field_names(release_config["category_fields"])
    release_config["preserve_string_fields"] = normalize_field_names(
        release_config["preserve_string_fields"]
    )
    return release_config

def normalize_field_names(fields: list[str]) -> list[str]:
    return [field.lower() for field in fields]

def release_files(
    drafts_dir: Path,
    releases_dir: Path,
    assets_dir: Path,
    release_config: dict,
    content_type: str,
):
    drafts = list(drafts_dir.glob("*.md"))
    marked = [path for path in drafts if is_marked_for_release(path)]

    if not marked:
        typer.echo("No drafts for release.")
        return

    for path in marked:
        release_draft(path, releases_dir, assets_dir, release_config, content_type)

def is_marked_for_release(path: Path) -> bool:
    post = frontmatter.load(path)
    return post.metadata.get("release") is True

def validate_draft(
    post: frontmatter.Post,
    path: Path,
    release_config: dict,
    content_type: str,
) -> bool:
    required_fields = release_config["required_fields"]
    required = list(required_fields["common"])
    required.extend(required_fields.get(content_type, []))
    required.extend(required_fields.get(PATH_KEYS_BY_TYPE.get(content_type, ""), []))

    missing = [key for key in required if not has_frontmatter_value(post, key)]

    if missing:
        typer.echo(f"Missing {missing}: {path}")
        return False

    return True

def has_frontmatter_value(post: frontmatter.Post, key: str) -> bool:
    if key not in post.metadata:
        return False

    value = post.metadata[key]
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, (list, dict)):
        return bool(value)

    return True

def remove_build_fields(post: frontmatter.Post, release_config: dict):
    build_fields = set(release_config["build_fields"])
    for field in list(post.metadata):
        if field.lower() in build_fields:
            post.metadata.pop(field, None)

def normalize_frontmatter(post: frontmatter.Post, release_config: dict):
    normalized = {}

    for key, value in post.metadata.items():
        normalized[key.lower()] = normalize_frontmatter_value(key, value, release_config)

    post.metadata = normalized

def normalize_frontmatter_value(key: str, value, release_config: dict):
    preserve_string_fields = set(release_config["preserve_string_fields"])
    preserve_string_fields.update(release_config["frontmatter_image_fields"])

    if key.lower() in preserve_string_fields:
        return value

    if key.lower() in release_config["category_fields"]:
        return normalize_category_value(value)

    if isinstance(value, str):
        return value.lower()

    if isinstance(value, list):
        return [normalize_frontmatter_value(key, item, release_config) for item in value]

    if isinstance(value, dict):
        return {
            nested_key.lower(): normalize_frontmatter_value(nested_key, nested_value, release_config)
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

def consolidate_images(
    post: frontmatter.Post,
    draft_path: Path,
    assets_dir: Path,
    release_config: dict,
) -> dict[str, str]:
    slug = slugify(post.metadata["title"])
    target_dir = assets_dir / slug
    replacements = {}

    for _, image_path in IMAGE_PATTERN.findall(post.content):
        replacement = consolidate_image(image_path, draft_path, target_dir, slug)
        if replacement is not None:
            replacements[image_path] = replacement

    for field in release_config["frontmatter_image_fields"]:
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

def compile_draft(
    post: frontmatter.Post,
    draft_path: Path,
    assets_dir: Path,
    release_config: dict,
) -> frontmatter.Post:
    remove_build_fields(post, release_config)
    normalize_frontmatter(post, release_config)
    replacements = consolidate_images(post, draft_path, assets_dir, release_config)
    replace_image_path(post, replacements)
    return post

def release_draft(
    path: Path,
    target_dir: Path,
    assets_dir: Path,
    release_config: dict,
    content_type: str,
):
    post = frontmatter.load(path)

    if not validate_draft(post, path, release_config, content_type):
        raise typer.Exit(1)

    compiled = compile_draft(post, path, assets_dir, release_config)

    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / path.name

    if target.exists():
        typer.echo(f"Draft {target} already exists.")
        raise typer.Exit(1)

    target.write_text(frontmatter.dumps(compiled), encoding="utf-8")
    path.unlink()

    typer.echo(f"Draft {target} released.")
