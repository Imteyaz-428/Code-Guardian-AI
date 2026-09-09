import os
import utils

from services.user import UserService


def main():
    user = UserService()
    print(user)


def calculate():
    return 10 + 20