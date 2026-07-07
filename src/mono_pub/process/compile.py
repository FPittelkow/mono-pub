from pathlib import Path

import frontmatter

from mono_pub.process.assets import consolidate_images, replace_image_path


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
            nested_key.lower(): normalize_frontmatter_value(
                nested_key,
                nested_value,
                release_config,
            )
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
