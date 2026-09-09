import ast


class CodeStructureAnalyzer(ast.NodeVisitor):

    def __init__(self):
        self.functions = []
        self.methods = []
        self.classes = []

        # Keeps track of whether we are currently inside a class
        self.current_class = None

    def visit_ClassDef(self, node):
        """
        Extract a class and then inspect everything inside it.
        """

        self.classes.append({
            "name": node.name,
            "line": node.lineno
        })

        previous_class = self.current_class

        self.current_class = node.name

        # Visit methods and nested classes
        self.generic_visit(node)

        self.current_class = previous_class

    def visit_FunctionDef(self, node):
        """
        Extract normal functions and methods.
        """

        if self.current_class is not None:

            self.methods.append({
                "name": node.name,
                "line": node.lineno,
                "class": self.current_class
            })

        else:

            self.functions.append({
                "name": node.name,
                "line": node.lineno
            })

        # Continue visiting nested functions
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        """
        Extract async functions and methods.
        """

        if self.current_class is not None:

            self.methods.append({
                "name": node.name,
                "line": node.lineno,
                "class": self.current_class
            })

        else:

            self.functions.append({
                "name": node.name,
                "line": node.lineno
            })

        self.generic_visit(node)

    def analyze(self, source_code):
        """
        Analyze Python source code.

        Returns:
            Dictionary containing classes, functions and methods.
        """

        # Reset state for every file
        self.functions = []
        self.methods = []
        self.classes = []
        self.current_class = None

        tree = ast.parse(source_code)

        self.visit(tree)

        return {
            "functions": self.functions,
            "methods": self.methods,
            "classes": self.classes
        }

    def analyze_file(self, file_path):
        """
        Analyze a Python file directly.
        """

        with open(file_path, "r", encoding="utf-8") as file:
            source_code = file.read()

        return self.analyze(source_code)