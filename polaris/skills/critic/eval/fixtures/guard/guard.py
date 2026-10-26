DESTRUCTIVE = ("reset --hard", "branch -D", "push --force")


def allowed(argv: list[str], dirty: bool) -> bool:
    command = " ".join(argv)
    if dirty and any(fragment in command for fragment in DESTRUCTIVE):
        return False
    return True
