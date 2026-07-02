from copy import deepcopy

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


def get_release_config(config: dict) -> dict:
    release_config = deepcopy(DEFAULT_RELEASE_CONFIG)
    configured_release = config.get("release", {})

    release_config.update(configured_release)
    release_config["required_fields"] = (
        DEFAULT_RELEASE_CONFIG["required_fields"]
        | configured_release.get("required_fields", {})
    )

    for key in (
        "build_fields",
        "frontmatter_image_fields",
        "category_fields",
        "preserve_string_fields",
    ):
        release_config[key] = normalize_field_names(release_config[key])

    return release_config


def normalize_field_names(fields: list[str]) -> list[str]:
    return [field.lower() for field in fields]


def path_key_for(content_type: str) -> str:
    return PATH_KEYS_BY_TYPE[content_type]
