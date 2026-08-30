def calculate_total(cart):
    total = 0

    for item in cart:
        total += item["price"] * item["quantity"]

    return total


def apply_discount(total, discount):
    if discount is None:
        return total
    return total - (total * discount)


cart = [
    {"name": "Laptop", "price": 60000, "quantity": 1},
    {"name": "Mouse", "price": 1500, "quantity": 2},
]

total = calculate_total(cart)

# Intentional bug: discount is None
discount = None

final_price = apply_discount(total, discount)

print("Final Price:", final_price)
