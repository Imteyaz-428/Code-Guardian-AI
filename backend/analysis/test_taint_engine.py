"""Regression corpus for the project-level taint engine.

Positive cases must produce a rule-matched vulnerability; negative cases (safe
patterns) must not.  Run:  pytest backend/analysis/test_taint_engine.py
"""
from __future__ import annotations

import ast
import textwrap

import pytest

from backend.analysis.taint_analysis import TaintAnalyzer


def analyze(files: dict[str, str]) -> list[tuple[str, str, str]]:
    """Return [(function_id, rule_id, sink_name)] for the given {file: source}."""
    functions = {}
    for file, source in files.items():
        tree = ast.parse(textwrap.dedent(source))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions[f"{file}::{node.name}"] = node
    result = TaintAnalyzer().analyze_project(functions)
    return [(v.function_id, v.rule_id, v.sink_name) for v in result.vulnerabilities]


def rules(source: str) -> set[str]:
    return {rule for _, rule, _ in analyze({"app.py": source})}


# ------------------------------------------------------------------
# Must be detected
# ------------------------------------------------------------------

POSITIVE = {
    "flask request.args.get + concat": ("SQL_INJECTION", '''
        def f(cur):
            name = request.args.get("name")
            cur.execute("SELECT * FROM t WHERE n = '" + name + "'")
    '''),
    "request.form subscript + f-string": ("SQL_INJECTION", '''
        def f(cur):
            name = request.form["name"]
            cur.execute(f"SELECT * FROM t WHERE n = '{name}'")
    '''),
    "input() source (original behaviour)": ("SQL_INJECTION", '''
        def f(cur):
            name = input("n: ")
            cur.execute("SELECT " + name)
    '''),
    "pydantic body param named request": ("SQL_INJECTION", '''
        @app.post("/q")
        def f(request: QueryRequest):
            cur.execute("SELECT * FROM t WHERE n = '" + request.name + "'")
    '''),
    "fastapi route parameter": ("SQL_INJECTION", '''
        @app.get("/u")
        def f(name: str):
            cur.execute(f"SELECT * FROM u WHERE n = '{name}'")
    '''),
    "sink inside try/with/for": ("SQL_INJECTION", '''
        def f(conn):
            name = request.args.get("n")
            try:
                with conn.cursor() as cur:
                    for _ in range(1):
                        cur.execute("SELECT " + name)
            except Exception:
                pass
    '''),
    "return of sink call": ("SQL_INJECTION", '''
        def f(cur):
            name = request.args.get("n")
            return cur.execute("SELECT " + name)
    '''),
    "taint through .strip() and +=": ("SQL_INJECTION", '''
        def f(cur):
            name = request.args.get("n").strip()
            q = "SELECT * FROM t WHERE n = "
            q += name
            cur.execute(q)
    '''),
    "str.format": ("SQL_INJECTION", '''
        def f(cur):
            name = request.args.get("n")
            cur.execute("SELECT {}".format(name))
    '''),
    "os.system": ("COMMAND_INJECTION", '''
        def f():
            p = request.args.get("p")
            os.system("ls " + p)
    '''),
    "subprocess shell=True": ("COMMAND_INJECTION", '''
        def f():
            c = request.args.get("c")
            subprocess.run(c, shell=True)
    '''),
    "subprocess sh -c list": ("COMMAND_INJECTION", '''
        def f():
            c = request.args.get("c")
            subprocess.run(["sh", "-c", c])
    '''),
    "eval": ("CODE_INJECTION", '''
        def f():
            eval(request.args.get("e"))
    '''),
    "open path": ("PATH_TRAVERSAL", '''
        def f():
            with open(request.args["file"]) as fh:
                return fh.read()
    '''),
    "pickle.loads": ("UNSAFE_DESERIALIZATION", '''
        def f():
            return pickle.loads(request.data)
    '''),
    "yaml.load default loader": ("UNSAFE_DESERIALIZATION", '''
        def f():
            return yaml.load(request.data)
    '''),
    "requests.get ssrf": ("SSRF", '''
        def f():
            return requests.get(request.args["u"])
    '''),
    "sys.argv": ("COMMAND_INJECTION", '''
        def f():
            os.system(sys.argv[1])
    '''),
}


@pytest.mark.parametrize("name", POSITIVE)
def test_detected(name):
    expected, source = POSITIVE[name]
    assert expected in rules(source), name


def test_path_neutralisation_does_not_hide_sql_or_mixed_flows():
    # .suffix is safe for paths, NOT for SQL
    assert "SQL_INJECTION" in rules('''
        def f(cur):
            ext = Path(request.args["f"]).suffix
            cur.execute("SELECT * FROM t WHERE e = '" + ext + "'")
    ''')
    # one neutralised and one raw tainted part: still a path traversal
    assert "PATH_TRAVERSAL" in rules('''
        def f():
            ext = Path(request.args["a"]).suffix
            return open("/data/" + ext + request.args["b"])
    ''')


def test_stdlib_call_is_not_resolved_to_same_named_project_method():
    # `run` is also a project function; subprocess.run must not call into it.
    found = analyze({"app.py": '''
        def run(self, command):
            cmd = list(command)
            return subprocess.run(cmd)

        @app.post("/x")
        def handler(request: Body):
            subprocess.run(["echo", request.name])
    '''})
    assert found == []


def test_tuple_return_is_tracked_element_wise():
    found = analyze({"app.py": '''
        def make(url):
            work = tempfile.mkdtemp()
            return url, work

        @app.post("/x")
        def handler(request: Body):
            target, work = make(request.url)
            shutil.rmtree(work)
    '''})
    assert found == []          # `work` never carries request data
    found = analyze({"app.py": '''
        def make(url):
            work = tempfile.mkdtemp()
            return url, work

        @app.post("/x")
        def handler(request: Body):
            target, work = make(request.url)
            shutil.rmtree(target)
    '''})
    assert [r for _, r, _ in found] == ["PATH_TRAVERSAL"]   # `target` does


def test_argv_list_variable_is_not_shell_injection():
    assert rules('''
        def f():
            c = request.args.get("c")
            cmd = ["git", "-c", "x=y", "clone", c]
            subprocess.run(cmd, check=True)
    ''') == set()
    assert "COMMAND_INJECTION" in rules('''
        def f():
            c = request.args.get("c")
            cmd = ["sh", "-c", c]
            subprocess.run(cmd)
    ''')


def test_interprocedural_flow_is_attributed_to_the_sink_function():
    found = analyze({"app.py": '''
        def helper(cur, q):
            cur.execute("SELECT " + q)

        @app.get("/x")
        def handler(name: str):
            helper(cur, name)
    '''})
    assert found == [("app.py::helper", "SQL_INJECTION", "execute")]


def test_same_function_name_in_two_files_is_analysed_separately():
    found = analyze({
        "a.py": '''
            def hello(cur):
                cur.execute("SELECT " + request.args["x"])
        ''',
        "b.py": '''
            def hello(cur):
                cur.execute("SELECT 1")
        ''',
    })
    assert found == [("a.py::hello", "SQL_INJECTION", "execute")]


def test_findings_carry_file_and_function():
    functions = {"pkg/api.py::get_user": ast.parse(textwrap.dedent('''
        def get_user(cur):
            cur.execute("SELECT " + request.args["x"])
    ''')).body[0]}
    result = TaintAnalyzer().analyze_project(functions)
    vuln = result.vulnerabilities[0].to_dict()
    assert (vuln["file"], vuln["function"]) == ("pkg/api.py", "get_user")


# ------------------------------------------------------------------
# Must NOT be flagged (safe patterns / false-positive guards)
# ------------------------------------------------------------------

NEGATIVE = {
    "parameterised query": '''
        def f(cur):
            name = request.args.get("n")
            cur.execute("SELECT * FROM t WHERE n = %s", (name,))
    ''',
    "parameterised query (keyword params)": '''
        def f(cur):
            name = request.args.get("n")
            cur.execute("SELECT * FROM t WHERE n = :n", params={"n": name})
    ''',
    "constant query": '''
        def f(cur):
            cur.execute("SELECT 1")
    ''',
    "int() sanitises": '''
        def f(cur):
            uid = int(request.args.get("id"))
            cur.execute(f"SELECT * FROM t WHERE id = {uid}")
    ''',
    "subprocess argv list, no shell": '''
        def f():
            p = request.args.get("p")
            subprocess.run(["ls", p])
    ''',
    "app.run is not a command sink": '''
        def f():
            app.run(request.args.get("x"))
    ''',
    "yaml.load with SafeLoader": '''
        def f():
            return yaml.load(request.data, Loader=yaml.SafeLoader)
    ''',
    "requests.post body is not ssrf": '''
        def f():
            return requests.post("https://api.example.com", data=request.data)
    ''',
    "fastapi Depends and int path param": '''
        @app.get("/u/{uid}")
        def f(uid: int, db=Depends(get_db)):
            db.execute(f"SELECT * FROM u WHERE id = {uid}")
    ''',
    "flask int converter": '''
        @app.route("/u/<int:uid>")
        def f(uid):
            cur.execute(f"SELECT * FROM u WHERE id = {uid}")
    ''',
    "unannotated request object (flask/django view)": '''
        @app.route("/x")
        def f(request):
            cur.execute("SELECT * FROM t WHERE u = " + str(request.user.id))
    ''',
    "non-route function params are not tainted": '''
        def f(cur, name):
            cur.execute("SELECT " + name)
    ''',
    "secure_filename sanitises": '''
        def f():
            return open(secure_filename(request.args["f"]))
    ''',
    "uuid name + user extension (real FP in RAG project)": '''
        @app.post("/upload")
        def upload(file: UploadFile = File(...)):
            extension = Path(file.filename).suffix
            stored = f"{uuid.uuid4()}{extension}"
            with open(UPLOAD_DIR / stored, "wb") as buf:
                shutil.copyfileobj(file.file, buf)
    ''',
    "os.path.basename neutralises path traversal": '''
        def f():
            return open(os.path.join("/data", os.path.basename(request.args["f"])))
    ''',
}


@pytest.mark.parametrize("name", NEGATIVE)
def test_not_flagged(name):
    assert rules(NEGATIVE[name]) == set(), name
