import ast

from backend.analysis.call_graph import CallGraphAnalyzer


def test_basic_call_graph():
    source = """
def main():
    login()
    calculate()

def login():
    validate()

def validate():
    pass

def calculate():
    pass
"""

    tree = ast.parse(source)

    analyzer = CallGraphAnalyzer()

    graph = analyzer.analyze({
        "main.py": tree
    })

    assert graph.get_callees("main.py::main") == [
        "main.py::calculate",
        "main.py::login",
    ]

    assert graph.get_callees("main.py::login") == [
        "main.py::validate",
    ]

    assert graph.get_callers("main.py::validate") == [
        "main.py::login",
    ]

    assert graph.get_statistics() == {
        "functions": 4,
        "calls": 3,
    }
    
    
import ast

from backend.analysis.call_graph import CallGraphAnalyzer


def test_basic_call_graph():
    source = """
def main():
    login()
    calculate()

def login():
    validate()

def validate():
    pass

def calculate():
    pass
"""

    tree = ast.parse(source)

    analyzer = CallGraphAnalyzer()

    graph = analyzer.analyze({
        "main.py": tree
    })

    assert graph.get_callees("main.py::main") == [
        "main.py::calculate",
        "main.py::login",
    ]

    assert graph.get_callees("main.py::login") == [
        "main.py::validate",
    ]

    assert graph.get_callers("main.py::validate") == [
        "main.py::login",
    ]

    assert graph.get_statistics() == {
        "functions": 4,
        "calls": 3,
    }


def test_cross_file_call_graph():
    main_source = """
from auth import login

def main():
    login()
"""

    auth_source = """
from database import get_user

def login():
    get_user()
"""

    database_source = """
def get_user():
    pass
"""

    trees = {
        "main.py": ast.parse(main_source),
        "auth.py": ast.parse(auth_source),
        "database.py": ast.parse(database_source),
    }

    analyzer = CallGraphAnalyzer()
    graph = analyzer.analyze(trees)

    assert graph.get_callees("main.py::main") == [
        "auth.py::login",
    ]

    assert graph.get_callees("auth.py::login") == [
        "database.py::get_user",
    ]

    assert graph.get_callers("auth.py::login") == [
        "main.py::main",
    ]

    assert graph.get_callers("database.py::get_user") == [
        "auth.py::login",
    ]

    assert graph.get_statistics() == {
        "functions": 3,
        "calls": 2,
    }
    
    
    
def test_class_method_call_graph():
    source = """
class UserService:

    def login(self):
        self.validate()

    def validate(self):
        pass
"""

    tree = ast.parse(source)

    analyzer = CallGraphAnalyzer()

    graph = analyzer.analyze({
        "service.py": tree
    })

    assert graph.get_all_functions() == [
        "service.py::UserService::login",
        "service.py::UserService::validate",
    ]

    assert graph.get_callees(
        "service.py::UserService::login"
    ) == [
        "service.py::UserService::validate",
    ]

    assert graph.get_callers(
        "service.py::UserService::validate"
    ) == [
        "service.py::UserService::login",
    ]

    assert graph.get_statistics() == {
        "functions": 2,
        "calls": 1,
    }
    
def test_same_method_name_in_different_classes():
    source = """
class UserService:

    def validate(self):
        pass

    def login(self):
        self.validate()


class PaymentService:

    def validate(self):
        pass

    def pay(self):
        self.validate()
"""

    tree = ast.parse(source)

    analyzer = CallGraphAnalyzer()

    graph = analyzer.analyze({
        "services.py": tree
    })

    assert graph.get_callees(
        "services.py::UserService::login"
    ) == [
        "services.py::UserService::validate",
    ]

    assert graph.get_callees(
        "services.py::PaymentService::pay"
    ) == [
        "services.py::PaymentService::validate",
    ]

    assert graph.get_callers(
        "services.py::UserService::validate"
    ) == [
        "services.py::UserService::login",
    ]

    assert graph.get_callers(
        "services.py::PaymentService::validate"
    ) == [
        "services.py::PaymentService::pay",
    ]

    assert graph.get_statistics() == {
        "functions": 4,
        "calls": 2,
    }
    
    
def test_from_import_function_resolution():
    main_source = """
from utils import calculate

def process():
    calculate()
"""

    utils_source = """
def calculate():
    pass
"""

    trees = {
        "main.py": ast.parse(main_source),
        "utils.py": ast.parse(utils_source),
    }

    analyzer = CallGraphAnalyzer()
    graph = analyzer.analyze(trees)

    assert graph.get_callees(
        "main.py::process"
    ) == [
        "utils.py::calculate",
    ]
    
    
    
def test_module_import_resolution():
    main_source = """
import utils

def process():
    utils.calculate()
"""

    utils_source = """
def calculate():
    pass
"""

    trees = {
        "main.py": ast.parse(main_source),
        "utils.py": ast.parse(utils_source),
    }

    analyzer = CallGraphAnalyzer()
    graph = analyzer.analyze(trees)

    assert graph.get_callees(
        "main.py::process"
    ) == [
        "utils.py::calculate",
    ]
    
    
def test_import_alias_resolution():
    main_source = """
from utils import calculate as calc

def process():
    calc()
"""

    utils_source = """
def calculate():
    pass
"""

    trees = {
        "main.py": ast.parse(main_source),
        "utils.py": ast.parse(utils_source),
    }

    analyzer = CallGraphAnalyzer()
    graph = analyzer.analyze(trees)

    assert graph.get_callees(
        "main.py::process"
    ) == [
        "utils.py::calculate",
    ]
    
def test_relative_import_function_resolution():
    main_source = """
from .utils import calculate

def process():
    calculate()
"""

    utils_source = """
def calculate():
    pass
"""

    trees = {
        "package/main.py": ast.parse(main_source),
        "package/utils.py": ast.parse(utils_source),
    }

    analyzer = CallGraphAnalyzer()
    graph = analyzer.analyze(trees)

    assert graph.get_callees(
        "package/main.py::process"
    ) == [
        "package/utils.py::calculate",
    ]
    
def test_relative_module_import_resolution():
    main_source = """
from . import utils

def process():
    utils.calculate()
"""

    utils_source = """
def calculate():
    pass
"""

    trees = {
        "package/main.py": ast.parse(main_source),
        "package/utils.py": ast.parse(utils_source),
    }

    analyzer = CallGraphAnalyzer()
    graph = analyzer.analyze(trees)

    assert graph.get_callees(
        "package/main.py::process"
    ) == [
        "package/utils.py::calculate",
    ]


def test_parent_package_relative_import_resolution():
    main_source = """
from ..utils import calculate

def process():
    calculate()
"""

    utils_source = """
def calculate():
    pass
"""

    trees = {
        "package/sub/main.py": ast.parse(main_source),
        "package/utils.py": ast.parse(utils_source),
    }

    analyzer = CallGraphAnalyzer()
    graph = analyzer.analyze(trees)

    assert graph.get_callees(
        "package/sub/main.py::process"
    ) == [
        "package/utils.py::calculate",
    ]