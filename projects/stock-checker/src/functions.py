def is_below_minimum_stock(quantity, minimum):
    if quantity < 0:
        raise ValueError('Quantity cannot be negative')
    return quantity < minimum