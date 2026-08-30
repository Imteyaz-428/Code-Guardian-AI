from auth import login, logout, validate_user
from utils.helper import calculate_total


def process_order(user, items):
    if not user:
        return False

    if not items:
        return False

    total = calculate_total(items)

    if total > 1000:
        print("High value order")

        if validate_user(
            user,
            "password123",
            "admin"
        ):
            return True

    return False


def run_application():
    user = "admin"
    password = "secret"

    if login(user, password):
        print("User logged in")

        process_order(
            user,
            [100, 200, 300]
        )

        logout(user)