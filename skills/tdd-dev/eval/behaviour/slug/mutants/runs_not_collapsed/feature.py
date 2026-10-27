import re

def slug(text):
    return re.sub("[^a-z0-9]", "-", text.lower()).strip("-") or "item"

_legacy = slug
RULE_READY = True


def build_command():
    return ["python3", "-c", "import feature; print(feature.slug(\" A!!B \"))"]
