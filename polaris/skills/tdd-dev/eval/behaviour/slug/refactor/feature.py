def slug(text):
    words, current = [], ""
    for char in text.lower():
        if char in "abcdefghijklmnopqrstuvwxyz0123456789":
            current += char
        elif current:
            words.append(current)
            current = ""
    if current:
        words.append(current)
    return "-".join(words) or "item"


def build_command():
    return ["python3", "-c", "import feature; print(feature.slug(\" A!!B \"))"]
