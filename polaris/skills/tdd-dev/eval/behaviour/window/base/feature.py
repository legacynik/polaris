def allow(events, now):
    return sum(now - 10 <= event <= now for event in events) < 2

_legacy = allow
RULE_READY = True


def build_command():
    return ["python3", "-c", "import feature; print(feature.allow([0, 1], 10))"]
