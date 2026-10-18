"""Make Code Guardian AI's taint analysis detect real-world flows.

Run once from the project root:   python apply_taint_patch.py
"""
from pathlib import Path

path = Path("backend/analysis/taint_analysis.py")
src = path.read_text()

if "_is_request_access" in src:
    raise SystemExit("already applied")


def replace_once(old: str, new: str) -> None:
    global src
    assert src.count(old) == 1, f"anchor not found exactly once:\n{old[:70]}"
    src = src.replace(old, new)


# 1 -- sources/sinks follow the rule engine -------------------------------
replace_once('''    DEFAULT_SOURCE_NAMES = {
        "input",
        "request_input",
        "get_user_input",
    }''', '''    DEFAULT_SOURCE_NAMES = {
        "input",
        "request_input",
        "get_user_input",
    } | {
        name
        for rule in VulnerabilityRuleEngine.DEFAULT_RULES
        for name in rule.source_names
    }

    REQUEST_OBJECTS = {"request", "req"}

    REQUEST_ATTRIBUTES = {
        "args", "form", "values", "json", "data", "files", "cookies",
        "headers", "GET", "POST", "query_params", "path_params", "body",
    }

    ROUTE_DECORATORS = {
        "get", "post", "put", "delete", "patch", "route", "api_route",
    }''')

replace_once('''    DEFAULT_SINK_NAMES = {
        "execute",
        "execute_query",
        "run_command",
    }''', '''    DEFAULT_SINK_NAMES = {
        "execute",
        "execute_query",
        "run_command",
    } | {
        name
        for rule in VulnerabilityRuleEngine.DEFAULT_RULES
        for name in rule.sink_names
    }''')

# 2 -- request.<attr> as a source -----------------------------------------
replace_once('''        # Direct variable reference.
        if isinstance(node, ast.Name):
            return tainted.get(node.id)
''', '''        # Direct variable reference.
        if isinstance(node, ast.Name):
            return tainted.get(node.id)

        # request.args / request.form / request.json ... (also reached
        # through subscripts and .get() calls via the child walk below).
        if self._is_request_access(node):
            return _TaintOrigin(
                source_name="request",
                source_line=getattr(node, "lineno", 0),
            )
''')

# helpers (placed before _call_name) --------------------------------------
replace_once('''    @staticmethod
    def _call_name(
        node: ast.Call,
    ) -> str:
''', '''    @staticmethod
    def _is_request_access(node: ast.AST) -> bool:
        """True for request.args, request.form, request.json, ..."""
        return (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id in TaintAnalyzer.REQUEST_OBJECTS
            and node.attr in TaintAnalyzer.REQUEST_ATTRIBUTES
        )

    @staticmethod
    def _handler_parameters(
        function_node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> list[str]:
        """Parameters of a web route handler: user-controlled input."""
        is_route = False

        for decorator in function_node.decorator_list:
            target = (
                decorator.func
                if isinstance(decorator, ast.Call)
                else decorator
            )
            if (
                isinstance(target, ast.Attribute)
                and target.attr in TaintAnalyzer.ROUTE_DECORATORS
            ):
                is_route = True
                break

        if not is_route:
            return []

        arguments = function_node.args
        positional = arguments.posonlyargs + arguments.args
        defaults = [None] * (
            len(positional) - len(arguments.defaults)
        ) + list(arguments.defaults)

        pairs = list(zip(positional, defaults)) + list(
            zip(arguments.kwonlyargs, arguments.kw_defaults)
        )

        names: list[str] = []

        for argument, default in pairs:
            if argument.arg in {"self", "cls", "request", "req"}:
                continue

            # Depends(...) / Security(...) are injected dependencies.
            if (
                isinstance(default, ast.Call)
                and TaintAnalyzer._call_name(default)
                in {"Depends", "Security"}
            ):
                continue

            names.append(argument.arg)

        return names

    @staticmethod
    def _call_name(
        node: ast.Call,
    ) -> str:
''')

# 3 + 4 -- analyse EVERY function; seed handler parameters ---------------
replace_once('''        for function_name, function_node in (
            function_by_name.items()
        ):

            state: dict[str, _TaintOrigin] = {}
''', '''        for function_node in functions.values():

            state: dict[str, _TaintOrigin] = {
                parameter: _TaintOrigin(
                    source_name="request",
                    source_line=function_node.lineno,
                )
                for parameter in self._handler_parameters(function_node)
            }
''')

# 5 -- project-level expression walker: request.* + method receivers -------
replace_once("""        if isinstance(
            node,
            ast.Name,
        ):
            return tainted.get(
                node.id
            )

        if isinstance(
            node,
            ast.Call,
        ):
""", """        if isinstance(
            node,
            ast.Name,
        ):
            return tainted.get(
                node.id
            )

        if self._is_request_access(node):
            return _TaintOrigin(
                source_name="request",
                source_line=getattr(node, "lineno", 0),
            )

        if isinstance(
            node,
            ast.Call,
        ):
""")

replace_once("""            # Unknown call: inspect arguments.
            for argument in node.args:""", """            # Unknown call: inspect the receiver first
            # (request.args.get(...), value.strip()), then the arguments.
            if isinstance(node.func, ast.Attribute):
                receiver_origin = self._expression_taint_interprocedural(
                    node.func.value,
                    tainted,
                    function_by_name,
                    source_names,
                    sanitizer_names,
                    summaries,
                    call_stack,
                )

                if receiver_origin is not None:
                    return receiver_origin

            for argument in node.args:""")

# 6 -- more statement kinds in the project-level walker -------------------
replace_once("""                if statement.value is None:
                    return return_origin

                return_origin = self._expression_taint_interprocedural(""", """                if statement.value is None:
                    return return_origin

                self._check_interprocedural_sinks(
                    statement.value,
                    tainted,
                    function_by_name,
                    source_names,
                    sanitizer_names,
                    sink_names,
                    result,
                    summaries,
                    current_stack,
                )

                return_origin = self._expression_taint_interprocedural(""")

replace_once("""        return return_origin

    # ============================================================
    # INTERPROCEDURAL EXPRESSION
    # ============================================================
""", """            # ----------------------------------------------------
            # x: T = value   /   x += value
            # ----------------------------------------------------

            if isinstance(statement, (ast.AnnAssign, ast.AugAssign)):

                if statement.value is not None:
                    origin = self._expression_taint_interprocedural(
                        statement.value,
                        tainted,
                        function_by_name,
                        source_names,
                        sanitizer_names,
                        summaries,
                        current_stack,
                    )

                    if (
                        origin is None
                        and isinstance(statement, ast.AugAssign)
                        and isinstance(statement.target, ast.Name)
                    ):
                        origin = tainted.get(statement.target.id)

                    self._assign_taint(statement.target, origin, tainted)

                    self._check_interprocedural_sinks(
                        statement.value,
                        tainted,
                        function_by_name,
                        source_names,
                        sanitizer_names,
                        sink_names,
                        result,
                        summaries,
                        current_stack,
                    )

                continue

            # ----------------------------------------------------
            # WITH / FOR / WHILE / TRY
            # ----------------------------------------------------

            blocks: list[list[ast.stmt]] | None = None

            if isinstance(statement, (ast.With, ast.AsyncWith)):
                for item in statement.items:
                    self._check_interprocedural_sinks(
                        item.context_expr,
                        tainted,
                        function_by_name,
                        source_names,
                        sanitizer_names,
                        sink_names,
                        result,
                        summaries,
                        current_stack,
                    )

                    if item.optional_vars is not None:
                        self._assign_taint(
                            item.optional_vars,
                            self._expression_taint_interprocedural(
                                item.context_expr,
                                tainted,
                                function_by_name,
                                source_names,
                                sanitizer_names,
                                summaries,
                                current_stack,
                            ),
                            tainted,
                        )

                blocks = [statement.body]

            elif isinstance(statement, (ast.For, ast.AsyncFor)):
                self._check_interprocedural_sinks(
                    statement.iter,
                    tainted,
                    function_by_name,
                    source_names,
                    sanitizer_names,
                    sink_names,
                    result,
                    summaries,
                    current_stack,
                )

                self._assign_taint(
                    statement.target,
                    self._expression_taint_interprocedural(
                        statement.iter,
                        tainted,
                        function_by_name,
                        source_names,
                        sanitizer_names,
                        summaries,
                        current_stack,
                    ),
                    tainted,
                )

                blocks = [statement.body, statement.orelse]

            elif isinstance(statement, ast.While):
                blocks = [statement.body, statement.orelse]

            elif isinstance(
                statement, (ast.Try, getattr(ast, "TryStar", ast.Try))
            ):
                blocks = (
                    [statement.body]
                    + [handler.body for handler in statement.handlers]
                    + [statement.orelse, statement.finalbody]
                )

            if blocks is not None:
                for block in blocks:
                    if not block:
                        continue

                    self._execute_interprocedural(
                        function_node=self._temporary_block_function(
                            function_node,
                            block,
                        ),
                        tainted=tainted,
                        function_by_name=function_by_name,
                        source_names=source_names,
                        sanitizer_names=sanitizer_names,
                        sink_names=sink_names,
                        result=result,
                        summaries=summaries,
                        call_stack=current_stack,
                    )

        return return_origin

    # ============================================================
    # INTERPROCEDURAL EXPRESSION
    # ============================================================
""")

path.write_text(src)
print("patched", path)