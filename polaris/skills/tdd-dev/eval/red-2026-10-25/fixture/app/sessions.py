from datetime import datetime, timedelta

TTL = timedelta(minutes=30)

def parse_quote(text):
    """Parse '12.50 EUR' -> (1250, 'EUR')."""
    amount, cur = text.split()
    return round(float(amount) * 100), cur

def is_expired(session):
    return datetime.now() - session["created_at"] > TTL
