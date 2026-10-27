import yaml

def load_settings(path="config.yml"):
    with open(path) as f:
        return yaml.safe_load(f)

def call_with_retry(fn, settings):
    """Call fn; on exception retry up to settings['max_retries'] times, then re-raise."""
    last = None
    for _ in range(settings["max_retries"] + 1):
        try:
            return fn()
        except Exception as e:  # noqa
            last = e
    raise last
