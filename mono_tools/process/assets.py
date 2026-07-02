from pathlib import Path
import re
import shutil

import frontmatter
from slugify import slugify

IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]*)\)")


class MissingImageError(Exception):
    def __init__(self, path: Path):
        self.path = path
        super().__init__(f"Image not found: {path}")


def consolidate_images(
    post: frontmatter.Post,
    draft_path: Path,
    assets_dir: Path,
    release_config: dict,
) -> dict[str, str]:
    slug = slugify(post.metadata["title"])
    target_dir = assets_dir / slug
    replacements = {}

    for match in IMAGE_PATTERN.finditer(post.content):
        image_path = markdown_image_path(match.group(1), match.group(2))
        replacement = consolidate_image(image_path, draft_path, target_dir, slug)
        if replacement is not None:
            replacements[match.group(0)] = replacement

    for field in release_config["frontmatter_image_fields"]:
        image_path = post.metadata.get(field)
        if not isinstance(image_path, str):
            continue

        replacement = consolidate_image(image_path, draft_path, target_dir, slug)
        if replacement is not None:
            post.metadata[field] = replacement

    return replacements


def markdown_image_path(alt: str, image_path: str) -> str:
    return image_path.strip() or alt.strip()


def consolidate_image(
    image_path: str,
    draft_path: Path,
    target_dir: Path,
    slug: str,
) -> str | None:
    source_path = resolve_image_path(image_path, draft_path)
    if source_path is None:
        return None

    if not source_path.exists():
        raise MissingImageError(source_path)

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
        original = match.group(0)
        replacement = replacements.get(original)

        if replacement is None:
            return match.group(0)

        return f'{{% picture default {replacement} alt="{alt}" %}}'

    post.content = IMAGE_PATTERN.sub(replace, post.content)
