import ast

from backend.analysis.function_collector import FunctionCollector


class CallGraph:
    """
    Represents function-to-function call relationships
    within an analyzed Python repository.
    """

    def __init__(self):
        # caller -> set of callees
        self.calls = {}

        # callee -> set of callers
        self.called_by = {}

    def add_function(self, function_id):
        """Register a function as a node in the call graph."""
        if function_id not in self.calls:
            self.calls[function_id] = set()

        if function_id not in self.called_by:
            self.called_by[function_id] = set()

    def add_call(self, caller_id, callee_id):
        """Add a caller -> callee relationship."""
        self.add_function(caller_id)
        self.add_function(callee_id)

        self.calls[caller_id].add(callee_id)
        self.called_by[callee_id].add(caller_id)

    def get_callees(self, function_id):
        """Return functions called by the given function."""
        return sorted(self.calls.get(function_id, set()))

    def get_callers(self, function_id):
        """Return functions that call the given function."""
        return sorted(self.called_by.get(function_id, set()))

    def get_all_functions(self):
        """Return all function nodes."""
        return sorted(self.calls.keys())

    def get_edges(self):
        """Return all caller -> callee edges."""
        edges = []

        for caller, callees in self.calls.items():
            for callee in callees:
                edges.append((caller, callee))

        return sorted(edges)

    def get_statistics(self):
        """Return basic call graph statistics."""
        functions = len(self.calls)
        edges = sum(len(callees) for callees in self.calls.values())

        return {
            "functions": functions,
            "calls": edges,
        }
        
        
        



class CallGraphAnalyzer:
    """
    Builds a call graph from Python AST trees.

    The analyzer identifies function-to-function calls
    between functions defined inside the analyzed repository.

    Resolution supports:
    - same-file functions
    - same-class methods
    - cross-file functions
    - from module import function
    - import module
    - import aliases
    - from-import aliases
    """

    def __init__(self):
        self.graph = CallGraph()

        # file -> imported symbols
        #
        # Example:
        # {
        #     "main.py": {
        #         "login": ("auth", "login"),
        #         "calc": ("utils", "calculate")
        #     }
        # }
        self.imports = {}

        # file -> module name
        self.module_names = {}

    def analyze(self, trees):
        """
        Analyze a collection of parsed AST trees.

        Parameters:
            trees: dictionary mapping file paths to AST trees.

        Returns:
            CallGraph
        """

        self.graph = CallGraph()
        self.imports = {}
        self.module_names = {}

        functions = self._collect_functions(trees)

        self._build_module_index(trees)
        self._collect_imports(trees)

        # Register every function as a graph node.
        for function_id in functions:
            self.graph.add_function(function_id)

        # Resolve calls.
        for caller_id, function_node in functions.items():
            calls = self._find_calls(function_node)

            for call_node in calls:
                callee_id = self._resolve_call(
                    call_node,
                    caller_id,
                    functions,
                )

                if callee_id:
                    self.graph.add_call(
                        caller_id,
                        callee_id,
                    )

        return self.graph

    def _collect_functions(self, trees):
        """
        Collect all functions and methods from the AST trees.
        """

        functions = {}

        for file_path, tree in trees.items():
            visitor = FunctionCollector(file_path)
            visitor.visit(tree)

            functions.update(visitor.functions)

        return functions

    def _build_module_index(self, trees):
        """
        Build a mapping between Python module names and files.

        Example:

            auth.py
                -> auth

            utils/helpers.py
                -> utils.helpers
        """

        for file_path in trees:
            path = file_path.replace("\\", "/")

            if path.endswith(".py"):
                path = path[:-3]

            if path.endswith("/__init__"):
                path = path[:-9]

            module_name = path.replace("/", ".")

            self.module_names[module_name] = file_path

    def _collect_imports(self, trees):
        """
        Collect import information for each source file.

        Supports:
            import module
            import module as alias
            from module import function
            from module import function as alias
            from .module import function
            from ..module import function
            from . import module
        """

        for file_path, tree in trees.items():
            self.imports[file_path] = {}

            for node in ast.walk(tree):

               
                # import module
               
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        local_name = (
                            alias.asname
                            or alias.name.split(".")[0]
                        )

                        self.imports[file_path][local_name] = (
                            alias.name,
                            None,
                        )

               
                # from module import function
               
                elif isinstance(node, ast.ImportFrom):
                    module_name = self._resolve_import_module(
                        file_path,
                        node.module,
                        node.level,
                    )

                    if module_name is None:
                        continue

                    for alias in node.names:
                        local_name = alias.asname or alias.name

                        self.imports[file_path][local_name] = (
                            module_name,
                            alias.name,
                        )

    def _resolve_import_module(
        self,
        file_path,
        module,
        level,
    ):
        """
        Resolve an absolute or relative Python import
        into a normalized module name.

        Examples:

            package/main.py
            from .utils import calculate

            -> package.utils

            package/sub/main.py
            from ..utils import calculate

            -> package.utils
        """

        # Absolute import
        if level == 0:
            return module

        path = file_path.replace("\\", "/")

        if path.endswith(".py"):
            path = path[:-3]

        # Remove __init__ because it represents the package itself.
        if path.endswith("/__init__"):
            path = path[:-9]

        parts = path.split("/")

        # The current file's package.
        if len(parts) > 1:
            package_parts = parts[:-1]
        else:
            package_parts = []

        # Each additional relative-import level moves
        # one package upward.
        #
        # level=1 -> current package
        # level=2 -> parent package
        # level=3 -> grandparent package
        remove_count = level - 1

        if remove_count > len(package_parts):
            return None

        if remove_count:
            package_parts = package_parts[:-remove_count]

        # `from . import utils`
        if module:
            module_parts = module.split(".")
            full_parts = package_parts + module_parts
        else:
            full_parts = package_parts

        if not full_parts:
            return None

        return ".".join(full_parts)
    def _find_calls(self, function_node):
        """
        Find AST Call nodes inside a function.
        """

        calls = []

        for node in ast.walk(function_node):
            if isinstance(node, ast.Call):
                calls.append(node)

        return calls

    def _get_name_parts(self, node):
        """
        Convert an AST expression into name components.

        Examples:

            calculate()
                -> ["calculate"]

            utils.calculate()
                -> ["utils", "calculate"]

            package.utils.calculate()
                -> ["package", "utils", "calculate"]
        """

        if isinstance(node, ast.Name):
            return [node.id]

        if isinstance(node, ast.Attribute):
            parts = self._get_name_parts(node.value)

            if parts:
                return parts + [node.attr]

        return []

    def _resolve_call(self, call_node, caller_id, functions):
        """
        Resolve a call using increasingly broader strategies.

        Resolution order:

        1. Same-class method
        2. Imported module/function
        3. Same-file function
        4. Unique repository-wide function
        """

        caller_file = caller_id.split("::")[0]
        call_parts = self._get_name_parts(call_node.func)

        if not call_parts:
            return None

        call_name = call_parts[-1]

       
        # 1. Same-class method
       

        caller_parts = caller_id.split("::")

        if len(caller_parts) >= 3:
            caller_class = caller_parts[-2]

            same_class_matches = [
                function_id
                for function_id in functions
                if function_id.startswith(
                    f"{caller_file}::{caller_class}::"
                )
                and function_id.split("::")[-1] == call_name
            ]

            if same_class_matches:
                return same_class_matches[0]

        # 2. Import-aware resolution
       

        imported_symbols = self.imports.get(
            caller_file,
            {},
        )

        first_part = call_parts[0]

        if first_part in imported_symbols:
            module_name, imported_name = imported_symbols[first_part]

            
            # from module import function
            
            if imported_name is not None:
                if len(call_parts) == 1:
                    target_name = imported_name

                    matches = [
                        function_id
                        for function_id in functions
                        if self._function_module(function_id)
                        == module_name
                        and function_id.split("::")[-1]
                        == target_name
                    ]

                    if len(matches) == 1:
                        return matches[0]

               
                # from module import Class
                # followed by Class.method()
               
                if len(call_parts) >= 2:
                    class_name = imported_name
                    method_name = call_parts[-1]

                    matches = [
                        function_id
                        for function_id in functions
                        if self._function_module(function_id)
                        == module_name
                        and len(function_id.split("::")) >= 3
                        and function_id.split("::")[-2] == class_name
                        and function_id.split("::")[-1] == method_name
                    ]

                    if len(matches) == 1:
                        return matches[0]

            
            # import module
            
            else:
                module_name = module_name

                if len(call_parts) >= 2:
                    target_name = call_parts[-1]

                    matches = [
                        function_id
                        for function_id in functions
                        if self._function_module(function_id)
                        == module_name
                        and function_id.split("::")[-1]
                        == target_name
                    ]

                    if len(matches) == 1:
                        return matches[0]

       
        # 3. Same-file function
       

        same_file_matches = [
            function_id
            for function_id in functions
            if function_id.startswith(
                f"{caller_file}::"
            )
            and function_id.split("::")[-1] == call_name
        ]

        if len(same_file_matches) == 1:
            return same_file_matches[0]

       
        # 4. Repository-wide unique function
       

        matches = [
            function_id
            for function_id in functions
            if function_id.split("::")[-1] == call_name
        ]

        if len(matches) == 1:
            return matches[0]

        # Ambiguous or external call.
        return None

    def _function_module(self, function_id):
        """
        Convert a function ID into its Python module name.

        Example:

            utils/helpers.py::calculate
                -> utils.helpers
        """

        file_path = function_id.split("::")[0]

        path = file_path.replace("\\", "/")

        if path.endswith(".py"):
            path = path[:-3]

        if path.endswith("/__init__"):
            path = path[:-9]

        return path.replace("/", ".")
    


# class FunctionCollector(ast.NodeVisitor):
#     """
#     Collect functions and methods from an AST.
#     """

#     def __init__(self, file_path):
#         self.file_path = file_path
#         self.functions = {}
#         self.class_stack = []

#     def visit_ClassDef(self, node):
#         self.class_stack.append(node.name)

#         self.generic_visit(node)

#         self.class_stack.pop()

#     def visit_FunctionDef(self, node):
#         function_id = self._build_function_id(node.name)

#         self.functions[function_id] = node

#         self.generic_visit(node)

#     def visit_AsyncFunctionDef(self, node):
#         function_id = self._build_function_id(node.name)

#         self.functions[function_id] = node

#         self.generic_visit(node)

#     def _build_function_id(self, function_name):
#         """
#         Build a unique function identifier.

#         Top-level function:
#             file.py::function

#         Class method:
#             file.py::ClassName::method
#         """

#         if self.class_stack:
#             class_name = "::".join(self.class_stack)
#             return f"{self.file_path}::{class_name}::{function_name}"

#         return f"{self.file_path}::{function_name}"