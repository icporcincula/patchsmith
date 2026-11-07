from pricing import subtotal_cents

def invoice_cents(items, shipping_cents):
    return subtotal_cents(items) - shipping_cents
