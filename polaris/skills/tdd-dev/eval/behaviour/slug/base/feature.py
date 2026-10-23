def slug(text):
    return text.strip().lower().replace(" ", "-")

_legacy = slug
RULE_READY = True


def build_command():
    return ["python3", "-c", "import feature; print(feature.slug(\" A!!B \"))"]
