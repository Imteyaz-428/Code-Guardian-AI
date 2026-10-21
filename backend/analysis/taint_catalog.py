"""Sources, sinks and route-handler knowledge for the taint engine.

Single source of truth: vulnerability_rules.py builds its sink sets from here.
Matching is syntactic (AST) and intentionally conservative about WHICH
arguments of a sink matter, so safe patterns such as parameterised SQL
(`cur.execute("... %s", (x,))`) or `subprocess.run([...])` are not flagged.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass

# ----------------------------------------------------------------
# Sources
# ----------------------------------------------------------------

REQUEST_ROOTS = frozenset({"request", "req"})
REQUEST_ATTRS = frozenset({
    "args", "form", "values", "json", "data", "files", "cookies", "headers",
    "GET", "POST", "query_params", "path_params", "body", "query", "matchdict",
    "params", "get_json", "get_data", "stream", "view_args",
})

SOURCE_NAMES = frozenset({
    "input", "request_input", "get_user_input", "request", "get_parameter",
    "route_parameter", "argv", "stdin",
})


def _dotted(node: ast.AST) -> str | None:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _chain(node: ast.AST) -> tuple[str | None, list[str]]:
    """Unwind a.b.c(...)[..] down to its root name and attribute list."""
    attrs: list[str] = []
    while True:
        if isinstance(node, ast.Call):
            node = node.func
        elif isinstance(node, ast.Attribute):
            attrs.append(node.attr)
            node = node.value
        elif isinstance(node, ast.Subscript):
            node = node.value
        elif isinstance(node, ast.Name):
            return node.id, list(reversed(attrs))
        else:
            return None, []


def expression_source(node: ast.AST) -> str | None:
    """Source name when `node` itself reads untrusted input, else None."""
    if not isinstance(node, (ast.Call, ast.Attribute, ast.Subscript)):
        return None
    root, attrs = _chain(node)
    if root is None:
        return None
    if root == "flask" and attrs[:1] == ["request"]:
        root, attrs = "request", attrs[1:]
    if root in REQUEST_ROOTS and attrs and attrs[0] in REQUEST_ATTRS:
        return "request"
    if root == "sys" and attrs[:1] == ["argv"]:
        return "argv"
    if root == "sys" and attrs[:2] in (["stdin", "read"], ["stdin", "readline"],
                                       ["stdin", "readlines"]):
        return "stdin"
    return None


# Receivers that are libraries, never project code: `subprocess.run(...)` must
# not be resolved to a project method that happens to be called `run`.
EXTERNAL_MODULES = frozenset({
    "os", "sys", "subprocess", "shutil", "json", "re", "math", "time", "datetime",
    "pathlib", "tempfile", "logging", "random", "uuid", "hashlib", "base64",
    "itertools", "functools", "collections", "typing", "asyncio", "threading",
    "requests", "httpx", "urllib", "yaml", "pickle", "marshal", "io", "glob",
    "socket", "ssl", "http", "sqlite3", "csv", "copy", "inspect", "ast", "zipfile",
    "tarfile", "torch", "np", "numpy", "pd", "pandas", "sqlalchemy", "pydantic",
    "fastapi", "flask", "django", "jwt", "bcrypt", "secrets", "string", "textwrap",
})


# ----------------------------------------------------------------
# Route handlers: their parameters are attacker-controlled
# ----------------------------------------------------------------

ROUTE_METHODS = frozenset({"get", "post", "put", "delete", "patch", "head",
                           "options", "route", "api_route", "websocket"})
SKIP_PARAM_NAMES = frozenset({"self", "cls", "response", "background_tasks",
                              "db", "session"})
# Unannotated `request` is the framework request object (Flask/Django style);
# its sources (request.args, request.GET, ...) are matched by expression_source.
# An annotated one (`request: CorrectionRequest`) is a request BODY model whose
# fields are attacker-controlled.
REQUEST_PARAM_NAMES = frozenset({"request", "req"})
SKIP_ANNOTATION_TOKENS = frozenset({"Request", "Response", "Session", "AsyncSession",
                                    "BackgroundTasks", "WebSocket", "Depends"})
# Framework coerces these types, so they cannot carry injection payloads.
SAFE_TYPES = frozenset({"int", "float", "bool", "UUID", "datetime", "date", "time",
                        "Decimal", "timedelta"})
_CONVERTER = re.compile(r"<(?:int|float|uuid)(?:\([^)]*\))?:(\w+)>")


def _route_decorators(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Call]:
    found = []
    for dec in func.decorator_list:
        if (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                and dec.func.attr in ROUTE_METHODS):
            found.append(dec)
    return found


def is_route_handler(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return bool(_route_decorators(func))


def route_parameters(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    typed_by_route: set[str] = set()
    for dec in _route_decorators(func):
        if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
            typed_by_route.update(_CONVERTER.findall(dec.args[0].value))

    a = func.args
    positional = list(a.posonlyargs) + list(a.args)
    defaults = [None] * (len(positional) - len(a.defaults)) + list(a.defaults)
    params = list(zip(positional, defaults)) + list(zip(a.kwonlyargs, a.kw_defaults))

    out = []
    for arg, default in params:
        if arg.arg in SKIP_PARAM_NAMES or arg.arg in typed_by_route:
            continue
        if arg.arg in REQUEST_PARAM_NAMES and arg.annotation is None:
            continue
        if isinstance(default, ast.Call):
            callee = default.func
            callee_name = callee.id if isinstance(callee, ast.Name) else getattr(callee, "attr", "")
            if callee_name in {"Depends", "Security"}:
                continue
        annotation = ast.unparse(arg.annotation) if arg.annotation is not None else ""
        idents = set(re.findall(r"[A-Za-z_]+", annotation))
        if idents & SKIP_ANNOTATION_TOKENS:
            continue
        if idents & SAFE_TYPES and not idents & {"str", "bytes", "Any"}:
            continue
        out.append(arg.arg)
    return out


# ----------------------------------------------------------------
# Sinks
# ----------------------------------------------------------------

RULE_KWARGS: dict[str, frozenset[str]] = {
    "SQL_INJECTION": frozenset({"query", "sql", "statement", "operation"}),
    "COMMAND_INJECTION": frozenset({"command", "cmd", "args"}),
    "CODE_INJECTION": frozenset({"source", "expression", "expr", "code"}),
    "PATH_TRAVERSAL": frozenset({"path", "file", "filename", "fname", "filepath"}),
    "UNSAFE_DESERIALIZATION": frozenset({"data", "stream", "s", "bytes_object"}),
    "SSRF": frozenset({"url"}),
    "XSS": frozenset({"content", "source", "template_string", "s"}),
}
_SHELLS = {"sh", "bash", "zsh", "dash", "cmd", "cmd.exe", "powershell", "pwsh"}


@dataclass(frozen=True)
class SinkSpec:
    rule_id: str
    names: frozenset[str]
    # None = any receiver; "" = bare call (`open(x)`); otherwise dotted receiver
    receivers: frozenset[str] | None = None
    args: str = "first"            # "first" = only the query/command/path argument
    shell_sensitive: bool = False  # subprocess: list argv without shell is safe
    safe_markers: tuple[str, ...] = ()  # e.g. yaml Loader=SafeLoader

    def canonical_names(self) -> set[str]:
        result: set[str] = set()
        for name in self.names:
            if self.receivers is None:
                result.add(name)
                continue
            for receiver in self.receivers:
                result.add(f"{receiver}.{name}" if receiver else name)
        return result


SINKS: tuple[SinkSpec, ...] = (
    SinkSpec("SQL_INJECTION", frozenset({"execute", "executemany", "executescript",
             "execute_query", "execute_sql", "raw_query", "raw"})),
    SinkSpec("SQL_INJECTION", frozenset({"text"}), frozenset({""})),
    SinkSpec("COMMAND_INJECTION", frozenset({"system", "popen"}), frozenset({"os", ""})),
    SinkSpec("COMMAND_INJECTION", frozenset({"run", "call", "check_call", "check_output",
             "Popen", "getoutput", "getstatusoutput"}), frozenset({"subprocess"}),
             shell_sensitive=True),
    SinkSpec("COMMAND_INJECTION", frozenset({"Popen", "check_output", "check_call",
             "getoutput"}), frozenset({""}), shell_sensitive=True),
    SinkSpec("COMMAND_INJECTION", frozenset({"run_command", "execute_command"}), None, args="all"),
    SinkSpec("CODE_INJECTION", frozenset({"eval", "exec"}), frozenset({""})),
    SinkSpec("PATH_TRAVERSAL", frozenset({"open"}), frozenset({"", "io", "os"})),
    SinkSpec("PATH_TRAVERSAL", frozenset({"send_file", "FileResponse"}), None),
    SinkSpec("PATH_TRAVERSAL", frozenset({"remove", "unlink", "rmdir", "listdir"}), frozenset({"os"})),
    SinkSpec("PATH_TRAVERSAL", frozenset({"rmtree"}), frozenset({"shutil"})),
    SinkSpec("PATH_TRAVERSAL", frozenset({"open_file", "read_file", "write_file",
             "remove_file"}), None, args="all"),
    SinkSpec("UNSAFE_DESERIALIZATION", frozenset({"loads", "load"}),
             frozenset({"pickle", "cPickle", "dill", "marshal"})),
    SinkSpec("UNSAFE_DESERIALIZATION", frozenset({"load", "unsafe_load", "full_load"}),
             frozenset({"yaml"}), safe_markers=("SafeLoader", "CSafeLoader")),
    SinkSpec("UNSAFE_DESERIALIZATION", frozenset({"decode"}), frozenset({"jsonpickle"})),
    SinkSpec("SSRF", frozenset({"get", "post", "put", "delete", "head", "patch", "request"}),
             frozenset({"requests", "httpx"})),
    SinkSpec("SSRF", frozenset({"urlopen"}), frozenset({"", "urllib.request", "urllib2"})),
    SinkSpec("XSS", frozenset({"render_template_string", "Markup", "mark_safe",
             "HTMLResponse", "render_html"})),
)


def sink_names_for(rule_id: str) -> frozenset[str]:
    names: set[str] = set()
    for spec in SINKS:
        if spec.rule_id == rule_id:
            names |= spec.canonical_names()
    return frozenset(names)


def _call_parts(call: ast.Call) -> tuple[str, str | None] | None:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id, ""
    if isinstance(func, ast.Attribute):
        return func.attr, _dotted(func.value)
    return None


def has_shell_true(call: ast.Call) -> bool:
    return any(k.arg == "shell" and isinstance(k.value, ast.Constant)
               and k.value.value is True for k in call.keywords)


def _launches_shell(argv: ast.AST) -> bool:
    """["sh", "-c", ...] runs a shell; ["git", "-c", ...] does not."""
    if isinstance(argv, (ast.List, ast.Tuple)) and argv.elts:
        head = argv.elts[0]
        return isinstance(head, ast.Constant) and head.value in _SHELLS
    return False


def argv_list(node: ast.AST) -> bool | None:
    """True/False when `node` builds an argv list (False = it starts a shell),
    None when it is not recognisably an argv list."""
    if isinstance(node, (ast.List, ast.Tuple)):
        return not _launches_shell(node)
    if isinstance(node, ast.Call):
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        if name in {"list", "tuple", "split"}:
            return True
    return None


def _is_safe_call(call: ast.Call, spec: SinkSpec) -> bool:
    if spec.shell_sensitive:
        shell_true = any(k.arg == "shell" and isinstance(k.value, ast.Constant)
                         and k.value.value is True for k in call.keywords)
        first = call.args[0] if call.args else None
        if not shell_true and isinstance(first, (ast.List, ast.Tuple)):
            if not _launches_shell(first):
                return True
    if spec.safe_markers:
        for k in call.keywords:
            if k.arg in ("Loader", "loader") and any(m in ast.unparse(k.value)
                                                      for m in spec.safe_markers):
                return True
    return False


def match_sink(call: ast.Call) -> tuple[SinkSpec, str] | None:
    """Return (spec, canonical sink name) when `call` is a known sink."""
    parts = _call_parts(call)
    if parts is None:
        return None
    name, receiver = parts
    for spec in SINKS:
        if name not in spec.names:
            continue
        if spec.receivers is not None and (receiver is None or receiver not in spec.receivers):
            continue
        if _is_safe_call(call, spec):
            continue
        canonical = name if spec.receivers is None or not receiver else f"{receiver}.{name}"
        return spec, canonical
    return None


def sink_arguments(call: ast.Call, spec: SinkSpec) -> list[ast.AST]:
    if spec.args == "all":
        nodes = list(call.args) + [k.value for k in call.keywords]
    else:
        kwargs = RULE_KWARGS.get(spec.rule_id, frozenset())
        nodes = list(call.args[:1]) + [k.value for k in call.keywords if k.arg in kwargs]
    return [n.value if isinstance(n, ast.Starred) else n for n in nodes]
