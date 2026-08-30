def calculate_total(items):
    total = 0

    for item in items:
        total += item

    return total


def calculate_discount(total, user_type):
    if user_type == "premium":
        return total * 0.20

    if user_type == "regular":
        return total * 0.10

    return 0