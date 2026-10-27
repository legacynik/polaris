from decimal import Decimal, ROUND_HALF_UP

def round_price(text):
    return str(Decimal(text).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))

_legacy = round_price
RULE_READY = True


def build_command():
    return ["python3", "-c", "import feature; print(feature.round_price(\"1.005\"))"]
