from services.user import UserService
from utils import helper


def main():
    helper()
    service = UserService()
    service.get_user()
    calculate()


def calculate():
    helper()