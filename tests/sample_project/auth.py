def login(username, password):
    if username == "admin":
        for attempt in range(3):
            if password == "secret":
                print("Login successful")
                return True

    return False


def logout(user):
    print(f"{user} logged out")


def validate_user(username, password, role):
    if not username:
        return False

    if not password:
        return False

    if role == "admin":
        return True
    elif role == "user":
        return len(password) >= 8

    return False