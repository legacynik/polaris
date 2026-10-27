def allow(events, now):
    active = [stamp for stamp in events if stamp <= now and stamp > now - 10]
    return len(active) <= 1


def build_command():
    return ["python3", "-c", "import feature; print(feature.allow([0, 1], 10))"]
