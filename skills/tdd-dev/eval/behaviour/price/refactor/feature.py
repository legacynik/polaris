from decimal import Decimal, ROUND_HALF_UP

def round_price(text):
    cents = Decimal(text).scaleb(2).to_integral_value(rounding=ROUND_HALF_UP)
    return format(cents.scaleb(-2), ".2f")


def build_command():
    return ["python3", "-c", "import feature; print(feature.round_price(\"1.005\"))"]
