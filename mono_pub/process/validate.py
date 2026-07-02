import frontmatter

from mono_pub.process.release_config import PATH_KEYS_BY_TYPE


def missing_required_fields(
    post: frontmatter.Post,
    release_config: dict,
    content_type: str,
) -> list[str]:
    required_fields = release_config["required_fields"]
    required = list(required_fields["common"])
    required.extend(required_fields.get(content_type, []))
    required.extend(required_fields.get(PATH_KEYS_BY_TYPE.get(content_type, ""), []))

    return [key for key in required if not has_frontmatter_value(post, key)]


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
