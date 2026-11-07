def subtotal_cents(items):
    return sum(item["price_cents"] for item in items)
